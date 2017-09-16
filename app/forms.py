# -*- coding: utf-8 -*-
import datetime
import pytz

from dateutil.parser import parse as datetime_parse

from django.conf import settings
from django.core.exceptions import ValidationError
from django.forms import forms, fields
from django.utils.crypto import get_random_string
from django.utils.functional import cached_property
from social_django.models import UserSocialAuth


class WebHookForm(forms.Form):
    token = fields.CharField()

    def clean_token(self):
        token = self.cleaned_data['token']
        if token != settings.SLACK_VERIFICATION_TOKEN:
            raise ValidationError('invalid token')

        return None

    def team_id(self):
        raise NotImplementedError()

    @cached_property
    def extra_data(self):
        return UserSocialAuth.get_social_auth('slack', self.team_id).extra_data


class CreateButtonForm(WebHookForm):
    team_id = fields.CharField()
    text = fields.CharField()
    channel_id = fields.CharField()

    def clean(self):
        data = super(CreateButtonForm, self).clean()

        timezone = pytz.timezone(self.extra_data.get('timezone'))
        now = datetime.datetime.now().astimezone(timezone)
        try:
            remind_time = datetime_parse(data['text'], default=now, fuzzy=True)
        except ValueError:
            remind_time = now + datetime.timedelta(days=1)

        data['timestamp'] = int(remind_time.timestamp())
        data['callback_id'] = get_random_string()

        return data

    @property
    def team_id(self):
        return self.data['team_id']


class StopReminderForm(WebHookForm):
    callback_id = fields.CharField()

    def clean(self):
        data = super(StopReminderForm, self).clean()
        for field in ('user', 'original_message'):
            data[field] = self.data.get(field)

        return data

    @property
    def team_id(self):
        return self.data['team']['id']


class ProfileForm(forms.Form):
    timezone = fields.TypedChoiceField(
        label='timezone',
        choices=((x, x) for x in pytz.all_timezones),
    )
