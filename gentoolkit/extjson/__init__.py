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

    def default(self, obj):
        if isinstance(obj, (datetime.date, datetime.datetime, datetime.time)):
            return arrow.get(obj).isoformat()
        if isinstance(obj, arrow.Arrow):
            return obj.isoformat()
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
