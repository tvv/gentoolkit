# -*- coding: utf-8 -*-
"""
API
------

Поддерживает:

* arrow.Arrow
* datetime.date, datetime.datetime, datetime.time

Классы arrow.Arrow, datetime.date, datetime.datetime, datetime.time преобразовываются в строку в формате ISO.
"""
try:
    from simplejson import loads as base_loads
    from simplejson import dumps as base_dumps
    from simplejson import JSONEncoder
except ImportError:
    from json import loads as base_loads
    from json import dumps as base_dumps
    from json import JSONEncoder

import datetime

import arrow


class Encoder(JSONEncoder):
    DATETIME_FORMAT = "YYYY-MM-DDTHH:mm:ss.SSSSSSZZ"
    DATE_FORMAT = "YYYY-MM-DD"
    TIME_FORMAT = "HH:mm:ss.SSSSSSZZ"

    def __init__(self, *args, **kwargs):
        self.l10n_context = kwargs.pop("l10n_context", None)
        self.datetime_as_timestamp = kwargs.pop("datetime_as_timestamp", False)
        super(Encoder, self).__init__(*args, **kwargs)

    def default(self, obj):
        if isinstance(obj, datetime.date):
            return arrow.get(obj).format(self.DATE_FORMAT)
        if isinstance(obj, datetime.time):
            return arrow.get(obj).format(self.TIME_FORMAT)
        if isinstance(obj, datetime.datetime):
            obj = arrow.get(obj)
        if isinstance(obj, arrow.Arrow):
            if self.datetime_as_timestamp:
                return obj.timestamp
            if self.l10n_context:
                obj = self.l10n_context.to_user_tz(obj)
            return obj.format(self.DATETIME_FORMAT)
        return JSONEncoder.default(self, obj)


def loads(*args, **kwargs):
    """
    Сериализация в JSON
    """
    return base_loads(*args, **kwargs)


def dumps(*args, **kwargs):
    """
    Десериализация из JSON
    """
    if 'cls' not in kwargs:
        kwargs['cls'] = Encoder
    return base_dumps(*args, **kwargs)
