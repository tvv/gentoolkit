# -*- coding: utf-8 -*-
import os
import sys
import logging
import datetime
import collections

import pytz
import arrow
from babel.dates import format_date, format_datetime, format_time
from babel.dates import format_timedelta
from babel.numbers import format_number, format_decimal, format_percent
from babel.numbers import parse_decimal, parse_number
from babel.support import Translations, NullTranslations

from gentoolkit.config import Proxy


class L10n(object):

    """
    Локализация текста, форматов даты и чисел
    """
    # текущий экземпляр класса
    instance = None

    # конфиг с настройками по умалчанию
    config = Proxy(
        {
            # default gettext translation domain
            'default_domain': 'messages',
            # http://en.wikipedia.org/wiki/ISO_3166-1
            'default_locale': 'en',
            # UTC offset in minutes
            'default_tz_offset': 0,
            # translation catalog source
            'sources': {
                # custom folder pointed by absolute path
                'folders': [],
                # modules and folder pars
                'modules': []
            }
        },
        'l10n'
    )

    def __new__(cls, *args, **kwargs):
        if cls.instance is None:
            cls.instance = super(L10n, cls).__new__(cls, *args, **kwargs)
            cls.__lookup_dirs = []
            cls.__translations = collections.defaultdict(dict)
        return cls.instance

    @property
    def default_domain(self):
        """
        Домен по умолчанию
        """
        return self.config.default_domain

    @property
    def default_locale(self):
        """
        Локаль по умолчанию
        """
        return self.config.default_locale

    @property
    def default_tz(self):
        """
        Временная зона по умолчанию
        """
        return pytz.FixedOffset(self.config.default_tz_offset)

    @property
    def lookup_dirs(self):
        """
        Каталоги переводов
        """
        return self.__lookup_dirs

    def gettext(self, msg, locale, domain=None):
        """
        Перевод строки

        :param str msg: строка для перевода
        :param str locale: локаль для перевода
        :param str domain: домен каталога переводов

        :return: str
        """
        return self.translation(locale, domain).ugettext(msg)

    def ngettext(self, singular, plural, n, locale, domain=None):
        """
        Перевод множественной формы

        :param str singular: строка для единственного числа
        :param str plural: строка для множественного числа
        :param number n: число
        :param str locale: локаль для перевода
        :param str domain: домен каталога переводов

        :return: str
        """
        return self.translation(locale, domain).ungettext(singular, plural, n)

    # Алиас для gettext
    _ = gettext

    # Алиас для ngettext
    _n = ngettext

    def format_date(self, d, frmt, locale, tz=None):
        """
        Форматирование даты в локаль с учетом формата и верменной зоны

        :param datetime.date,arrow.Arrow d: дата
        :param str frmt: формат строки
        :param str locale: локаль
        :param tzinfo tz: целевая временная зона

        :return: str
        """
        if isinstance(d, arrow.Arrow):
            d = d.date()
        if not isinstance(d, datetime.date):
            logging.warning(
                "Date [%s:%s] is not instance of (arrow.Arrow, datetime.date)",
                type(d), d)
            return None
        try:
            return format_date(d, frmt, tzinfo=tz, locale=locale)
        except:
            logging.exception("Fail to format date [%s,%s]", type(d), d)
            return None

    def format_datetime(self, dt, frmt, locale, tz=None):
        """
        Форматирование даты и времени в локаль с учетом формата и верменной зоны

        :param datetime.datetime,arrow.Arrow dt: дата
        :param str frmt: формат строки
        :param str locale: локаль
        :param tzinfo tz: целевая временная зона

        :return: str
        """
        if isinstance(dt, arrow.Arrow):
            dt = dt.datetime
        if not isinstance(dt, datetime.datetime):
            logging.warning(
                "DateTime [%s:%s] is not instance of (arrow.Arrow, datetime.datetime)",
                type(dt), dt)
            return None
        try:
            return format_datetime(dt, frmt, tzinfo=tz, locale=locale)
        except:
            logging.exception("Fail to format datetime [%s,%s]", type(dt), dt)
            return None

    def format_time(self, t, frmt, locale, tz=None):
        """
        Форматирование времени в локаль с учетом формата и верменной зоны

        :param datetime.time,arrow.Arrow t: время
        :param str frmt: формат строки
        :param str locale: локаль
        :param tzinfo tz: целевая временная зона

        :return: str
        """
        if isinstance(t, arrow.Arrow):
            t = t.time()
        if not isinstance(t, datetime.time):
            logging.warning(
                "Time [%s:%s] is not instance of (arrow.Arrow, datetime.time)",
                type(t), t)
            return None
        try:
            return format_time(t, frmt, tzinfo=tz, locale=locale)
        except:
            logging.exception("Fail to format time [%s,%s]", type(t), t)
            return None

    def format_timedelta(self, t, locale, threshold=None, granularity=None):
        """
        Форматирование периода в локаль с учетом формата и верменной зоны

        :param datetime.timedelta t: период
        :param str locale: локаль
        :param float threshold: порог
        :param str granularity: минимальная единица

        :return: str
        """
        if not isinstance(t, datetime.timedelta):
            logging.warning(
                "Timedelta [%s:%s] is not instance of (datetime.timedelta)",
                type(t), t)
            return None
        try:
            return format_timedelta(
                t, threshold=threshold, granularity=granularity,
                locale=locale)
        except:
            logging.exception("Fail to format time [%s,%s]", type(t), t)
            return None

    def format_number(self, num, locale):
        """
        Форматирование числа с учетом локали

        :param integer num: число
        :param str locale: локаль

        :return: str
        """
        try:
            return format_number(num, locale=locale)
        except:
            logging.exception("Fail to format number [%s,%s]", type(num), num)
            return None

    def format_decimal(self, num, locale, frmt=None):
        """
        Форматирование десятичного числа с учетом локали

        :param float num: число
        :param str locale: локаль

        :return: str
        """
        try:
            return format_decimal(num, locale=locale, format=frmt)
        except:
            logging.exception("Fail to format decimal [%s,%s]", type(num), num)
            return None

    def format_percent(self, num, locale):
        """
        Форматирование процентов с учетом локали

        :param float num: число
        :param str locale: локаль

        :return: str
        """
        try:
            return format_percent(num, locale=locale)
        except:
            logging.exception("Fail to format percent [%s,%s]", type(num), num)
            return None

    def parse_number(self, num, locale):
        """
        Преобразование строки в число с учетом локали

        :param str num: число
        :param str locale: локаль

        :return: integer
        """
        try:
            return parse_number(num, locale=locale)
        except:
            logging.exception("Fail to parse number [%s,%s]", type(num), num)
            return None

    def parse_decimal(self, num, locale):
        """
        Преобразование строки в десятичное число с учетом локали

        :param str num: число
        :param str locale: локаль

        :return: float
        """
        try:
            return parse_decimal(num, locale=locale)
        except:
            logging.exception("Fail to parse decimal [%s,%s]", type(num), num)
            return None

    def to_utc_tz(self, dt, tz):
        """
        Преобразование даты во временную зону UTC+0. Если в переданной дате не указана временная зона, то подставляется временная зона из переменной `tz` без изменения даты и времени.

        :param datetime.datetime,datetime.time,arrow.Arrow dt: время
        :param tzinfo tz: временная зона

        :return: datetime.datetime
        """
        if isinstance(dt, (datetime.datetime, datetime.time, arrow.Arrow)):
            if isinstance(dt, (datetime.datetime, datetime.time)):
                dt = arrow.get(dt, dt.tzinfo or tz)
            return dt.to('utc').datetime
        return dt

    def to_user_tz(self, dt, tz):
        """
        Преобразование даты в указанную временную зону. Если в переданной дате не указана временная зона, то подставляется временная зона из UTC без изменения даты и времени.

        :param datetime.datetime,datetime.time,arrow.Arrow dt: время
        :param tzinfo tz: временная зона

        :return: datetime.datetime
        """
        if isinstance(dt, (datetime.datetime, datetime.time, arrow.Arrow)):
            if isinstance(dt, (datetime.datetime, datetime.time)):
                dt = arrow.get(dt, dt.tzinfo or 'utc')
            return dt.to(tz).datetime
        return dt

    def __repr__(self):
        return "L10n"

    def __unicode__(self):
        return repr(self)

    def translation(self, locale, domain):
        """
        Получение объекта каталога переводов

        :param str locale: локаль
        :param str domain: домен

        :return: Translations
        """
        translation_dirs = self.build_dirs()
        if not domain:
            domain = self.config.default_domain
        locale = str(locale)
        translation = self.__translations[locale].get(domain, None)
        if not translation:
            logging.debug(
                "Translation for [locale=%s,domain=%s] not found. %s",
                locale, domain, self.__translations.items())
            translation = self.load(
                translation_dirs,
                locales=[locale, ],
                domain=domain)
            default_translation = \
                self.__translations[self.config.default_locale].get(
                    domain, None)
            if not default_translation:
                default_translation = self.load(
                    translation_dirs,
                    locales=[self.config.default_locale, ],
                    domain=domain)
                self.__translations[self.config.default_locale][domain] = \
                    default_translation
            translation.add_fallback(default_translation)
            self.__translations[locale][domain] = translation
        return translation

    def build_dirs(self):
        """
        Сбор путей до каталогов перевода

        :return: list
        """
        try:
            if not self.__lookup_dirs:
                for d in self.config.sources.folders:
                    d = os.path.abspath(d)
                    if os.path.exists(d):
                        self.__lookup_dirs.append(d)
                    else:
                        logging.error(
                            "Translation directory [%s] not found", d)
                for m in self.config.sources.modules:
                    for libpath in sys.path:
                        path = os.path.join(libpath, m[0], m[1])
                        if os.path.exists(path):
                            self.__lookup_dirs.append(path)
                            continue
                        logging.error(
                            "Translation in module [%s/%s] not found",
                            m[0], m[1])
                logging.info(
                    "Translation folders %s", self.__lookup_dirs)
            return self.__lookup_dirs
        except:
            logging.exception("Fail to build translation directory sources")
            return []

    def load(self, dirnames, locales, domain):
        """
        Инициализация объектов перевода. Просматриваются все переданные директории, все найдейнные переводы объединяются. Если перевод не найден возвращается `NullTranslations`

        :param list dirnames: список директорий
        :param list locales: список локалей
        :param str domain: домен

        :return: Translations
        """
        translation = None
        for dirname in dirnames:
            try:
                tmp = Translations.load(
                    dirname=dirname,
                    locales=locales,
                    domain=domain)
                if translation is None:
                    translation = tmp
                elif not isinstance(tmp, NullTranslations):
                    if isinstance(translation, NullTranslations):
                        translation = tmp
                    else:
                        translation.merge(tmp)
                logging.info(
                    "Translation loaded [dirname=%s, locales=%s, domain=%s].",
                    dirname, locales, domain)
            except:
                logging.exception(
                    "Fail to load translation [dirname=%s, locales=%s, domain=%s].",
                    dirname, locales, domain)
        if not translation:
            translation = NullTranslations()
        return translation


class Context(object):
    """
    Контекст перевода. Предоставляет доступ к классу L10n, локаль и временная зона предопределены.
    """
    def __init__(self, locale, tz_offset):
        """
        Конструктор

        :param str locale: текущая локаль
        :param int tz_offset: смещение в минутах относительно UTC+0
        """
        super(Context, self).__init__()
        self.__l10n = L10n()
        self.locale = locale or self.__l10n.default_locale
        self.tz = pytz.FixedOffset(tz_offset) or self.__l10n.default_tz

    def gettext(self, msg, domain=None):
        """
        Прокси для :py:meth:`.L10n.gettext`
        """
        return self.__l10n.gettext(msg, self.locale, domain)

    def ngettext(self, singular, plural, n, domain=None):
        """
        Прокси для :py:meth:`.L10n.ngettext`
        """
        return self.__l10n.ngettext(singular, plural, n, self.locale, domain)

    _ = gettext
    _n = ngettext

    def format_date(self, d, frmt):
        """
        Прокси для :py:meth:`.L10n.format_date`
        """
        return self.__l10n.format_date(d, frmt, self.locale, tz=self.tz)

    def format_datetime(self, dt, frmt):
        """
        Прокси для :py:meth:`.L10n.format_datetime`
        """
        return self.__l10n.format_datetime(dt, frmt, self.locale, tz=self.tz)

    def format_time(self, t, frmt):
        """
        Прокси для :py:meth:`.L10n.format_time`
        """
        return self.__l10n.format_time(t, frmt, self.locale, tz=self.tz)

    def format_timedelta(self, t, locale, threshold=None, granularity=None):
        """
        Прокси для :py:meth:`.L10n.format_timedelta`
        """
        return self.__l10n.format_timedelta(
            t, self.locale, threshold=threshold, granularity=granularity)

    def format_number(self, num):
        """
        Прокси для :py:meth:`.L10n.format_number`
        """
        return self.__l10n.format_number(num, self.locale)

    def format_decimal(self, num, frmt=None):
        """
        Прокси для :py:meth:`.L10n.format_decimal`
        """
        return self.__l10n.format_decimal(num, self.locale, frmt=frmt)

    def format_percent(self, num):
        """
        Прокси для :py:meth:`.L10n.format_percent`
        """
        return self.__l10n.format_percent(num, self.locale)

    def parse_number(self, num):
        """
        Прокси для :py:meth:`.L10n.parse_number`
        """
        return self.__l10n.format_percent(num, self.locale)

    def parse_decimal(self, num):
        """
        Прокси для :py:meth:`.L10n.parse_decimal`
        """
        return self.__l10n.format_percent(num, self.locale)

    def to_utc_tz(self, dt):
        """
        Прокси для :py:meth:`.L10n.to_utc_tz`
        """
        return self.__l10n.to_utc_tz(dt, self.tz)

    def to_user_tz(self, dt):
        """
        Прокси для :py:meth:`.L10n.to_user_tz`
        """
        return self.__l10n.to_user_tz(dt, self.tz)

    def __repr__(self):
        return "l10n.Context(locale=%s, tz=%s)" % (
            self.locale, str(self.tz.utcoffset()))

    def __unicode__(self):
        return repr(self)


instance = L10n()
