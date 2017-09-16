# -*- coding: utf-8 -*-
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.views.decorators.csrf import csrf_exempt
from social_django.models import UserSocialAuth

from app.caches import Reminder
from app.forms import ProfileForm, CreateButtonForm, StopReminderForm
from app.tasks import add_reminder_to_members, delete_reminder


@csrf_exempt
def create_button(req):
    if req.method != 'POST':
        return HttpResponseBadRequest()

    form = CreateButtonForm(req.POST)
    if not form.is_valid():
        return HttpResponseBadRequest(form.errors.as_json(), content_type='application/json')

    payload = form.cleaned_data
    add_reminder_to_members.delay(
        oauth_token=form.extra_data['access_token'],
        channel_id=payload['channel_id'],
        callback_id=payload['callback_id'],
        text=payload['text'],
        timestamp=payload['timestamp'],
    )

    return JsonResponse(data={
        'response_type': 'in_channel',
        'text': payload['text'],
        'attachments': [{
            'fallback': 'Failed.',
            'callback_id': payload['callback_id'],
            'color': '#808080',
            'actions': [
                {
                    'type': 'button',
                    'name': 'done',
                    'text': 'Done',
                    'style': 'primary',
                }
            ]
        }]
    })


@csrf_exempt
def stop_reminder(req):
    if req.method != 'POST':
        return HttpResponseBadRequest()

    form = StopReminderForm(json.loads(req.POST.get('payload')))
    if not form.is_valid():
        return HttpResponseBadRequest(form.errors.as_json(), content_type='application/json')

    payload = form.cleaned_data
    callback_id = payload['callback_id']
    user_id = payload['user'].get('id')

    cache = Reminder(callback_id, user_id)
    if not cache.get():
        return HttpResponseBadRequest(content='already done.')

    delete_reminder.delay(
        oauth_token=form.extra_data['access_token'],
        callback_id=callback_id,
        user_id=user_id,
    )

    return JsonResponse(data={
        'replace_original': False,
        'response_type': 'ephemeral',
        'text': '~{text}~'.format(**payload['original_message']),
    })


@login_required
def profile(req):
    auth = UserSocialAuth.objects.get(provider='slack', user_id=req.user.id)

    if req.method == 'POST':
        form = ProfileForm(req.POST)
        if not form.is_valid():
            return HttpResponseBadRequest(form.errors.as_json(), content_type='application/json')

        auth.extra_data.update(form.cleaned_data)
        auth.save()

        messages.add_message(req, messages.SUCCESS, 'update success.')
        return redirect('profile')

    form = ProfileForm(initial={'timezone': auth.extra_data.get('timezone')})
    return TemplateResponse(req, 'accounts/profile.html', {'form': form})


def top(req):
    return TemplateResponse(req, 'top.html')
