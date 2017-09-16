# -*- coding: utf-8 -*-
from slackclient import SlackClient

from .celery import app
from .caches import Reminder


@app.task(ignore_result=True)
def add_reminder_to_members(oauth_token=None, channel_id=None, callback_id=None, text='', timestamp=None):
    members = get_channel_members(oauth_token, channel_id)

    for user_id in members:
        add_reminder.delay(
            oauth_token=oauth_token,
            callback_id=callback_id,
            user_id=user_id,
            text=text,
            timestamp=timestamp
        )

    return len(members)


@app.task(ignore_result=True)
def add_reminder(oauth_token=None, callback_id=None, user_id=None, text='', timestamp=None):
    slack = SlackClient(oauth_token)
    res = slack.api_call(
        'reminders.add',
        text=text,
        time=timestamp,
        user=user_id
    )

    if not res.get('ok'):
        error = res.get('error')
        if error in ('cannot_add_bot',):
            return 'pass'
        else:
            raise RuntimeError(error)

    reminder_id = res.get('reminder').get('id')
    cache = Reminder(callback_id, user_id)
    cache.set(reminder_id, timeout=timestamp)
    return reminder_id


@app.task(ignore_result=True, default_retry_delay=5 * 60)
def delete_reminder(oauth_token=None, callback_id=None, user_id=None):
    cache = Reminder(callback_id, user_id)
    reminder_id = cache.get()
    if not reminder_id:
        raise RuntimeError('no key {}'.format(cache.key))

    slack = SlackClient(oauth_token)
    res = slack.api_call(
        'reminders.delete',
        reminder=reminder_id
    )
    if not res.get('ok'):
        raise RuntimeError(res.get('error'))

    cache.delete()
    return reminder_id


def get_channel_members(oauth_token=None, channel=None):
    slack = SlackClient(oauth_token)

    res = slack.api_call(
        'groups.info',
        channel=channel,
    )
    if res.get('ok'):
        return res.get('group').get('members')

    res = slack.api_call(
        'channels.info',
        channel=channel,
    )
    if res.get('ok'):
        return res.get('channel').get('members')

    raise RuntimeError(res.get('error'))
