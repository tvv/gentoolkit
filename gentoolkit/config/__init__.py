# -*- coding: utf-8 -*-
"""
Прокси `Proxy`
--------------

Прокси для доступа к глобальным настройкам с поддержкой значений по умолчанию.

Объект данного класса может использоваться в любом месте кода, для быстрого доступа к параметрам настройки.

Пример использования к классе::

    class A(object):
        config = Proxy({
            'default': {
                'dsn': 'mysql://root:root@localhost:3306/test'
                }
            },
            'db')

        def get_some(self):
            conn = get_connection(self.config.default)
            ....

Пример использования в модуле::

    config = Proxy({
        'host': 'localhost'
        })

    def get_image(name):
        return "%s/%s" % (config.host, name)

"""
import json
import os
import logging
import collections
import copy


__all__ = [
    'instance', 'get', 'init',
    'WrongConfigPrefix',
    'Config', 'Node', 'Proxy'
]


class WrongConfigPrefix(Exception):
    """
    Указан не верный префикс. Допускается str, unicode, list, tuple.
    """


class WrongExtends(Exception):
    """
    Указан не верный путь до родительских настроек
    """


class _notset:
    """
    Служебный класс
    """

notset = _notset()


class Proxy(object):
    """
    Прокси для доступа к глобальным настройкам с поддержкой значений по умолчанию.
    """
    def __init__(self, defaults, config_prefix=None, config=None):
        """
        Конструктор прокси

        :param dict defaults: словарь настроек по умолчанию
        :param str config_prefix: префикс для поиска параметров
        """
        global instance
        self._defaults = defaults
        if not isinstance(config_prefix, (list, tuple)):
            config_prefix = [config_prefix]
        self._config_prefix = config_prefix
        self._config = config or instance

    def get(self, name, default=notset):
        """
        Перегрузка метода поиска. Сначало проверяется глобальные настройки, потом значения по умолчанию.
        """
        try:
            return self._config.get(
                "{}.{}".format(".".join(self._config_prefix), name)
            )
        except AttributeError:
            return get_path(self._defaults, name, default=default)

    def __getitem__(self, name):
        """
        Перегрузка доступа по индексу. Сначало преверяется глобальные настройки, потом значения по умолчанию.
        """
        return self.get(name)

    def __contains__(self, name):
        try:
            self.get(name)
            return True
        except AttributeError:
            return False

    def __iter__(self):
        return iter(self.get(self._config_prefix, self._defaults))

    def __repr__(self):
        return "config.Proxy -> {}\n{}\nGlobal\n{}" % (
            self._config_prefix,
            self._defaults,
            get(self._config_prefix, default={})
        )

    def __unicode__(self):
        return repr(self)


class Config(object):

    """
    Объект хранит текущие настройки.
    """

    def __init__(self):
        super(Config, self).__init__()
        self._data = {}
        self._source = None

    def reset(self):
        self._data = {}
        self._source = None

    def init(self, cfg):
        """
        Инициализация настроек. Чтение файла с настройками.

        :param str cfg: абсолютный путь до файла настроек

        :return: None|Config
        """
        self._data = {}
        self._source = None

        if isinstance(cfg, dict):
            self._data = cfg
            self._source = "__dict__"
            return self
        elif os.path.exists(cfg):
            try:
                with open(cfg, "r") as fd:
                    self._data = json.load(fd)
                    self._source = cfg
                return self
            except:
                logging.exception("Config '%s' read fail", cfg)
        else:
            logging.error("Config at %s not found", cfg)
        raise Exception("Config not valid")

    def get(self, path, default=notset):
        """
        Получить значение настройки path.

        :param str path: строка с разделителем '.' (logger.syslog.ip)
        :param default: значение по умолчанию

        :return: Node|Any
        :raises AttributeError: если не найден и нет значения по умолчанию
        """
        return get_path(self._data, path, default=default)


    def __getitem__(self, name):
        """
        Перегрузка доступа к атрибутам класса.

        :param str,int name: имя атрибута

        :return: Any|Node
        :raises AttributeError: если не найден
        """
        return self.get(name)

    def __contains__(self, name):
        """
        Поддержка семантики проверки `in`. Проверка произвольной глубины.

        :param str name: строка с разделителем '.' (logger.syslog.ip)

        :return: Boolean
        """
        try:
            v = self.get(name)
            return True
        except AttributeError:
            return False
        except:
            logging.exception("contains check fail [%s]", name)
            return False

    def __iter__(self):
        """
        Возвращает итератор по корневым параметрам настроек
        """
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def __repr__(self):
        return "config.Config<source={}, data={}>".format(
            self._source, self._data
        )

    def __unicode__(self):
        return repr(self)


def get_path(data, path, default=notset):
    n = data
    p = path.split('.')
    while p:
        i = p.pop(0)
        if i not in n:
            if default != notset:
                return default
            raise AttributeError(path)

        n = n[i]
    return n


#: Объект настроек
instance = Config()

#: Инициализация настроек, ссылка на `Config.init`
init = instance.init

#: Получение параметров настройки, ссылка на `Config.get`
get = instance.get