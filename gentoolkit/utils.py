# -*- coding: utf-8 -*-
import functools
import copy


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'


def colored_text(text, color):
    return color + text + bcolors.ENDC


def get_record(default, key=None, data=None):
    if callable(default):
        default = default()
    else:
        default = copy.deepcopy(default)
    if not data:
        return default
    if key:
        default.update(data.get(key, {}) or {})
    else:
        default.update(data)
    return default


def get_record_list(default, key=None, data=None):
    if not data:
        return []
    return [get_record(default, key=key, data=i) for i in data]


def get_record_partial(default=None, key=None):
    return lambda d=None: get_record(default or {}, key=key, data=d)


def get_record_list_partial(default, key):
    return lambda d=None: get_record_list(default, key, data=d)


def remove_from_record_list(pk, data):
    return [i for i in data if data['id'] != pk]


def get_from_record_list(data, pk, default=None):
    for i in data:
        if i['id'] == pk:
            return i
    return default


def update_record_list(data, origin):
    for idx, i in enumerate(origin):
        if i['id'] == pk:
            origin[idx] = data
            return origin
    origin.append(data)
    return origin