# -*- coding: utf-8 -*-
import logging
import logging.handlers

from gentoolkit.config import Proxy
from gentoolkit.config import get as config_get


#: инстанс логгера по умолчанию
logger = None
#: наименование сервиса
service_name = None

config = Proxy(
    {
        'stdout': False,
        'format': "%%(asctime)s^%s^%%(message)s^%%(pathname)s:%%(lineno)s:%%(funcName)s",
        'event_format': "%(asctime)s %(message)s",
        'syslog': False,
        'levels': []
    },
    "logger"
)


class SyslogFormatter(logging.Formatter):

    def __init__(self, *args, **kwargs):
        kwargs["fmt"] = config.format
        super(SyslogFormatter, self).__init__(*args, **kwargs)


class ColoredFormatter(logging.Formatter):
    error_fmt = "\033[1;91m%(levelname)s %(asctime)s [%(pathname)s:%(lineno)s:%(funcName)s]\n  %(message)s\033[0m"
    warning_fmt = "\033[93m%(levelname)s %(asctime)s [%(pathname)s:%(lineno)s:%(funcName)s]\n  %(message)s\033[0m"
    other_fmt = "\033[94m%(levelname)s %(asctime)s [%(pathname)s:%(lineno)s:%(funcName)s]\033[0m\n  \033[92m%(message)s\033[0m"

    def __init__(self, *args, **kwargs):
        kwargs["fmt"] = self.other_fmt
        super(ColoredFormatter, self).__init__(*args, **kwargs)

    def format(self, record):
        fmt = self.other_fmt
        if record.levelname in ("ERROR", "CRITICAL"):
            fmt = self.error_fmt
        elif record.levelname == "WARNING":
            fmt = self.warning_fmt

        if hasattr(self, "_style"):
            self._style._fmt = fmt
        else:
            self._fmt = fmt
        return super(ColoredFormatter, self).format(record)


def init(name, debug=False, stdout=False):
    """
    Инициализация логгера

    :param string name: название сервиса
    :param boolean debug: режим отладки, по умолчанию True
    :param boolean stdout: вывод сообщений в консоль STDOUT, по умолчанию False
    """
    global logger
    global service_name
    if logger is not None:
        return logger

    service_name = name

    debug = True if debug else config_get('debug', debug)
    stdout = True if stdout else config.get('stdout', stdout)
    log_level = logging.DEBUG if debug else logging.INFO
    rootLogger = logging.getLogger()
    rootLogger.setLevel(log_level)

    if config['syslog']:
        handler = logging.handlers.SysLogHandler(
            address=(config.get('syslog.ip'), config.get('syslog.port')),
            facility=logging.handlers.SysLogHandler.LOG_USER)
        handler.setLevel(log_level)
        handler.setFormatter(SyslogFormatter())
        rootLogger.addHandler(handler)
    if stdout:
        stdout_formatter = ColoredFormatter()
        handler = logging.StreamHandler()
        handler.setLevel(log_level)
        handler.setFormatter(stdout_formatter)
        rootLogger.addHandler(handler)

    if not stdout and not config['syslog']:
        rootLogger.addHandler(logging.NullHandler())

    for name, level in config.get('levels', []):
        inst = logging.getLogger(name)
        inst.setLevel(level)

    logger = rootLogger
