# -*- coding: utf-8 -*-
"""
Интерфейс профайлера к Graphite серверу

Использование::

    with Profiler('goods.get'):
        do something or exception

    profiler = Profiler("goods.get")
    with profiler("info"):
        do something

    profiler.append("memmory", 300)
    profiler.flush()

    @profile()
    def func(a, b):
        pass

Настройки::

    {
        "profiler": {
            "env": "",
            "app": "",
            "address": ["127.0.0.1", 2023]
        }
    }

Правила именования метрики
--------------------------

Общий шаблон метрик `<env>.<app>.<hostname>.<<metric>>`.

Каждая метрика `<<metric>>` может содержать точки.

Суфикс метрики и способ агрегации:

* <<metric>>.sum - sum
* <<metric>>.avg - avg
* агрегация по умолчанию - avg

Агрегированная метрика не должна содержать метку агрегации (`sum`, `avg`). Например, `dev.dal.hosta.gearman.tasks.get_product.sum` записывается как `dev.dal.hosta.gearman.tasks.get_product`.

"""
import logging
import calendar
import datetime
import time
import socket

import arrow

from gentoolkit.config import Proxy


__all__ = ['Profiler', 'Timer', 'profile']


class Profiler(object):
    """
    Профайлер
    """

    def __init__(self, prefix=None, **config):
        """
        Конструктор

        :param str prefix: префикс имени метрики
        """
        super(Profiler, self).__init__()
        default = {
            'address': ('127.0.0.1', 2004),
            'env': "",
            'app': ""
        }
        default.update(config)
        self.config = Proxy(default, 'profiler')
        self.__timers = {}
        self.__report = []
        self.__prefix = ""
        if self.config.get('env', ""):
            self.__prefix += "%s." % self.config.env
        if self.config.get('app', ""):
            self.__prefix += "%s." % self.config.app
        self.__prefix += "%s." % socket.gethostname()
        if prefix:
            self.__prefix += prefix
        if self.__prefix[-1] != '.':
            self.__prefix += "."
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.begin('avg')

    def append(self, name, value, tm=None):
        """
        Добавить метрику

        :param str name: название метрики
        :param int value: значение
        :param int tm: время начала сбора метрики в секундах UTC+0
        """
        if not tm:
            tm = calendar.timegm(datetime.datetime.utcnow().utctimetuple())
        if name:
            self.__report.append(
                ("%s%s" % (self.__prefix, name), value, tm))
        else:
            logging.warning(
                "Metric is not valid name=%s, tm=%s, value=%s",
                name, tm, value)

    def begin(self, name, autoflush=True):
        """
        Возвращает таймер для сбора метрики с именем `name`.

        :param str name: название метрики

        :return: Timer
        """
        if name in self.__timers:
            logging.warning("Timer '%s' already exists", name)
            return self.__timers[name]
        timer = Timer(name, self, autoflush=autoflush)
        self.__timers[name] = timer
        return timer

    def end(self, name_or_instance):
        """
        Закрыть таймер и снять метрику

        :param str,Timer name_or_instance: назвение метрики или объект класса Timer
        """
        timer = name_or_instance
        if not isinstance(name_or_instance, Timer):
            timer = self.__timers.get(name_or_instance, None)
        if timer:
            self.append(timer.name, timer.elapsed, timer.start)
            del self.__timers[timer.name]
        else:
            logging.warning("Timer '%s' stopped but not defined")

    def flush(self):
        """
        Отправляет все метрики по одной на UDP адрес в формате `<metric_name> <metric_value> <metric_time>`
        """
        for timer in self.__timers.values():
            if timer.autoflush:
                timer.end()
            else:
                del self.__timers[timer.name]
        for name, value, tm in self.__report:
            message = "%s %s %d" % (name, str(value), tm)
            logging.debug("Profiler message [%s]", message)
            self.__socket.sendto(
                message,
                (self.config.address[0], self.config.address[1])
            )
        self.__report = []
        self.__timers = {}
        self.begin('avg')

    def __enter__(self):
        """
        Семантика `with`

        :return: Profiler
        """
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Обработчик не скрывает исключения в блоке `with`, все исключения должны быть обработаны внешним кодом.
        """
        self.flush()


class Timer(object):
    """
    Таймер
    """

    def __init__(self, name, profiler, autoflush=True):
        super(Timer, self).__init__()
        self.__profiler = profiler
        self.name = name
        self.start = arrow.utcnow().timestamp
        self.clock = time.time()
        self.autoflush = autoflush
        self.elapsed = 0

    def __enter__(self):
        """
        Семантика `with`

        :return: Timer
        """
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Обработчик не скрывает исключения в блоке `with`, все исключения должны быть обработаны внешним кодом.
        """
        self.end()

    def end(self):
        """
        Фиксирует значение профилируемого участка кода
        """
        self.elapsed = time.time() - self.clock
        self.__profiler.end(self)


def profile(prefix=None):
    """
    Декоратор
    """
    def dec(func):
        def inner_dec(*args, **kwargs):
            name = "%s.%s" % (func.__module__, func.__name__)
            with Profiler(prefix=prefix or name):
                return func(*args, **kwargs)
        return inner_dec
    return dec
