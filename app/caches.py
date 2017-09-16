# -*- coding: utf-8 -*-
from django.core.cache import cache


class Reminder:
    def __init__(self, *args):
        self.key = 'reminder.{}.{}'.format(*args)

    def get(self):
        return cache.get(self.key)

    def set(self, reminder, timeout):
        return cache.set(self.key, reminder, timeout)

    def delete(self):
        return cache.delete(self.key)
