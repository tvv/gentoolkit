# -*- coding: utf-8 -*-
"""
Модуль доступа к серверу memcached.

Данные хранятся в формате JSON.

Доступ к конкретному подключению::

    conn = rng_core.cache.instance.<conn_name>
    conn = rng_core.cache.instance['<conn_name>']

Настройки кеша::

    {
        "cache": {
            "conn_name": {
                // хост(ы) сервера кеширования
                "host": ['127.0.0.1:11211'],
                // дополнительные параметры
                "params": {},
                // префикс ключа
                "cache_prefix": "",
                // флаг хеширования ключей алгоритмом md5
                "hash_keys": false,
                // время жизни ключа по умолчанию
                "ttl": 60
            },
            // список заблокированных namespaces
            "disabled": [
                "namespaceA", "namespaceB"
            ]
        }
    }
"""

import logging
from functools import wraps
from hashlib import md5

import pylibmc

from gentoolkit.config import Proxy
from gentoolkit import extjson as json


DEFAULT_NAMESPACE = ''


def cached(key, namespace=None, ttl=None, conn_name=None):
    """
    Декоратор для кеширования результата вызова функции.

    :param str key: ключ
    :param str namespace: namespace для формирования ключа
    :param int ttl: время жизни кеша
    :param str conn_name: название подключения к серверу memcached

    :return: Any
    """
    def dec(func):
        @wraps(func)
        def inner_dec(*args, **kwargs):
            try:
                conn = instance[conn_name]
                if conn.enabled(namespace) and key:
                    key_str = key
                    if callable(key):
                        key_str = key(*args, **kwargs)
                    value = conn.get(key_str, namespace=namespace)
                    if value is None:
                        value = func(*args, **kwargs)
                        if value is not None:
                            conn.set(
                                key_str, value,
                                namespace=namespace,
                                ttl=ttl
                            )
                    return value
            except NotConfigured, e:
                logging.error(str(e))
            except Exception as exc:
                logging.exception("Fail to cache result of %s", func.__name__)
            return func(*args, **kwargs)
        return inner_dec
    return dec


class NotConfigured(Exception):
    """
    Исключение. Информация о подключении не найдена.
    """

    def __init__(self, name):
        super(NotConfigured, self).__init__("Connection %s not found" % name)
        self.name = name


class Backend(object):
    """
    Управление подключениями к серверу кеширования.
    """

    config = Proxy({}, "cache")
    instance = None

    def __new__(cls, *args, **kwargs):
        if cls.instance is None:
            cls.instance = super(Backend, cls).__new__(cls, *args, **kwargs)
        return cls.instance

    def __getattr__(self, name):
        try:
            return object.__getattribute__(name)
        except:
            return self.__get_connection(name)

    def __getitem__(self, name):
        return getattr(self, name)

    def __get_connection(self, name):
        if name in self.config:
            try:
                conn = self.__connect(name)
                if conn:
                    setattr(self, name, conn)
                    return conn
            except Exception as exc:
                if not isinstance(exc, NotConfigured):
                    send_critical(
                        "cache_connection_fail",
                        "connection fail for {}".format(
                            name
                        ),
                        params={
                            "conn_name": name,
                            "error": str(exc)
                        }
                    )
                    logging.exception(
                        "Fail to connect %s", self.config.get(name)
                    )
                raise
        raise NotConfigured(name)

    def __connect(self, name):
        if name not in self.config:
            send_critical(
                "cache_not_configured",
                "configuration {} not found".format(name),
                params={
                    "name": name
                }
            )
            raise NotConfigured(name)
        return Connection(
            Proxy(
                {
                    "params": {},
                    "ttl": 5,
                    "host": []
                },
                "cache.%s" % name
            )
        )


instance = Backend()


class Connection(object):
    """
    Адаптер подключения к серверу memcached.
    """

    disabled_config = Proxy(
        {},
        "cache.disabled"
    )

    def __init__(self, config):
        super(Connection, self).__init__()
        self.config = config
        self.params = {
            k: self.config.params.get(k)
            for k in self.config.params
        }
        self.__conn = pylibmc.Client(config.host, **self.params)

    def set(self, key, value, namespace=None, ttl=None):
        """
        Добавить значение в кеш.

        :param str key: ключ
        :param value: значение
        :param str namespace: namespace для формирования ключа
        :param int ttl: время жизни кеша

        :return: Bool
        """
        namespace = namespace or DEFAULT_NAMESPACE
        if self.enabled(namespace) and key:
            key = self.normalise_key(namespace, key)
            logging.debug(
                "cache::set %s, ttl=%d, namespace=%s",
                key,
                ttl if ttl else self.config.ttl,
                namespace
            )
            try:
                self.__conn.set(
                    key, json.dumps(value),
                    time=ttl if ttl else self.config.ttl
                )
                return True
            except Exception as exc:
                logging.exception(
                    "fail to set value at server %s", self.config.host
                )
        return False

    def set_multi(self, values, namespace=None, ttl=None):
        """
        Добавить несколько значение в кеш.

        :param list|tuple values:  пары ключ/значение
        :param str namespace: namespace для формирования ключа
        :param int ttl: время жизни кеша

        :return: Bool
        """
        namespace = namespace or DEFAULT_NAMESPACE
        if self.enabled(namespace) and values:
            values = dict(
                [
                    (self.normalise_key(namespace, k), json.dumps(v))
                    for k, v in values.items()
                ]
            )
            logging.debug(
                "cache::set_multi %s, ttl=%d, namespace=%s",
                values.keys(),
                ttl if ttl else self.config.ttl,
                namespace
            )
            try:
                self.__conn.set_multi(
                    values,
                    time=ttl if ttl else self.config.ttl
                )
                return True
            except Exception as exc:
                logging.exception(
                    "fail to set_multi value  at server %s", self.config.host
                )
        return False

    def get(self, key, namespace=None):
        """
        Получить значение из кеша.

        :param str key: ключ
        :param str namespace: namespace для формирования ключа

        :return: Any|None
        """
        namespace = namespace or DEFAULT_NAMESPACE
        if self.enabled(namespace) and key:
            key = self.normalise_key(namespace, key)
            logging.debug(
                "cache::get %s namespace=%s",
                key, namespace
            )
            try:
                if isinstance(key, (list, tuple)):
                    values = self.__conn.get_multi(key) or {}
                    return [
                        json.loads(value[k]) if value.get(k, None) else None
                        for k in key
                    ]
                else:
                    ret = self.__conn.get(key)
                    if ret:
                        ret = json.loads(ret)
                    return ret
            except Exception as exc:
                logging.exception(
                    "fail to get value at server %s", self.config.host
                )
                return None
        return None

    def add(self, key, value, namespace=None, ttl=None):
        """
        Добавить значение в кеш. Если значение уже установлено возвращает None.

        :param str key: ключ
        :param value: значение
        :param str namespace: namespace для формирования ключа
        :param int ttl: время жизни кеша

        :return: Bool
        """
        namespace = namespace or DEFAULT_NAMESPACE
        if self.enabled(namespace) and key:
            key = self.normalise_key(namespace, key)
            logging.debug(
                "cache::add %s, timeout=%d, namespace=%s",
                key,
                ttl if ttl else self.config.ttl,
                namespace
            )
            try:
                return self.__conn.add(
                    key, json.dumps(value),
                    time=ttl if ttl else self.config.ttl
                )
            except Exception as exc:
                logging.exception(
                    "fail to add value at server %s", self.config.host
                )
        return False

    def delete(self, key, namespace=None):
        """
        Удалить значение из кеша.

        :param str key: ключ
        :param str namespace: namespace для формирования ключа

        :return: Bool
        """
        namespace = namespace or DEFAULT_NAMESPACE
        if self.enabled(namespace) and key:
            key = self.normalise_key(namespace, key)
            logging.debug(
                "cache::delete %s namespace=%s",
                str(key), namespace
            )
            try:
                if isinstance(key, (list, tuple)):
                    return self.__conn.delete_multi(key)
                else:
                    return self.__conn.delete(key)
            except Exception as exc:
                logging.exception(
                    "fail to delete value at server", self.config.host
                )
        return False

    def incr(self, key, delta=1, namespace=None):
        """
        Инкримент.

        :param str key: ключ
        :param int delta: величина инкримента
        :param str namespace: namespace для формирования ключа

        :return: Bool
        """
        namespace = namespace or DEFAULT_NAMESPACE
        if self.enabled(namespace) and key:
            key = self.normalise_key(namespace, key)
            logging.debug(
                "cache::incr %s namespace=%s",
                str(key), namespace
            )
            try:
                if isinstance(key, (list, tuple)):
                    return all([self.__conn.incr(i, delta) for i in key])
                else:
                    return self.__conn.incr(key, delta)
            except Exception as exc:
                logging.exception(
                    "fail to incr value at server %s", self.config.host
                )
        return False

    def decr(self, key, delta=1, namespace=None):
        """
        Декримент.

        :param str key: ключ
        :param int delta: величина декримента
        :param str namespace: namespace для формирования ключа

        :return: Bool
        """
        namespace = namespace or DEFAULT_NAMESPACE
        if self.enabled(namespace) and key:
            key = self.normalise_key(namespace, key)
            logging.debug(
                "cache::incr %s namespace=%s",
                str(key), namespace
            )
            try:
                if isinstance(key, (list, tuple)):
                    return all([self.__conn.decr(i, delta) for i in key])
                else:
                    return self.__conn.decr(key, delta)
            except Exception as exc:
                logging.exception(
                    "fail to decr value at server %s", self.config.host
                )
        return False

    def invalidate(self, key, namespace=None):
        """
        Сброс кеша.

        :param str key: ключ
        :param str namespace: namespace для формирования ключа

        :return: None
        """
        logging.debug("invalidating %s namespace=%s", str(key), str(namespace))
        self.delete(key, namespace=namespace)

    @classmethod
    def enabled(cls, namespace):
        """
        Статус аспекта/namespace.

        :param str namespace: namespace для формирования ключа

        :return: Bool
        """
        if not namespace:
            return True
        return namespace not in self.disabled_config

    def normalise_key(self, namespace, key):
        """
        Нормализация ключа. Проверять необходимость добавления префикса,
        хеширования ключей (md5).

        :param str namespace: namespace для формирования ключа
        :param str key: ключ

        :return: str
        """
        if isinstance(key, (list, tuple)):
            return map(lambda k: self.normalise_key(namespace, k), key)
        if isinstance(key, unicode):
            key = key.encode('utf-8')
        elif not isinstance(key, (str, basestring)):
            key = repr(key)
        if isinstance(namespace, unicode):
            namespace = namespace.encode('utf-8')
        if namespace:
            key = "%s:%s" % (namespace, key)
        cache_prefix = self.config.get("cache_prefix", "")
        if cache_prefix:
            key = "%s_%s" % (cache_prefix, key)
        if self.config.get("hash_keys", False):
            key = md5(key).hexdigest()
        return key


class MutexException(Exception):
    pass


class Mutex(object):
    """
    Примитив синхронизации mutex, реализован на базе memcached сервера.
    """
    def __init__(self, server, key, namespace, ttl=60):
        """
        Конструктор

        :param str server: имя сервера
        :param str key: ключ
        :param str namespace: аспект
        :param int ttl: время жизни
        """
        super(Mutex, self).__init__()
        self.server = server
        self.cache = getattr(instance, server, None)
        self.key = key
        self.namespace = namespace
        self.ttl = ttl

    def update(self, ttl=None):
        """
        Продлить mutex

        :param int ttl: время жизни
        """
        ttl = ttl if ttl else self.ttl
        self.cache.set(self.key, 1, namespace=self.namespace, ttl=ttl)

    def lock(self):
        if not self.cache:
            logging.error(
                "Cache server not found. server=%s, key=%s, namespace=%s, ttl=%s",
                self.server, self.key, self.namespace, self.ttl
            )
            return False
        if not self.cache.add(self.key, 1, namespace=self.namespace, ttl=self.ttl):
            logging.error(
                "Lock fail. server=%s, key=%s, namespace=%s, ttl=%s",
                self.server, self.key, self.namespace, self.ttl
            )
            return False
        return True

    def release(self):
        if not self.cache:
            logging.error(
                "Cache server not found. server=%s, key=%s, namespace=%s, ttl=%s",
                self.server, self.key, self.namespace, self.ttl
            )
            return False
        return self.cache.delete(self.key, namespace=self.namespace)

