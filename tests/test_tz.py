# -*- coding: utf-8 -*-
import os
import datetime
import pytz
import calendar

import nose.tools

from gentoolkit import config
from gentoolkit import l10n


def test():
    config.init({
        "l10n": {
            "sources": {
                "folders": ["tests/locale"],
                "modules": []
            }
        }
    })

    check_l10n()
    check_context()


def check_l10n():
    # DATETIME with TIMEZONE
    utc_offset = pytz.FixedOffset(0)
    utc_datetime = datetime.datetime.now(utc_offset)
    one_hour_offset = pytz.FixedOffset(60)

    localised_datetime = l10n.instance.to_user_tz(utc_datetime, one_hour_offset)

    nose.tools.ok_(
        (localised_datetime - utc_datetime) == datetime.timedelta())

    utc_datetime_back = l10n.instance.to_utc_tz(localised_datetime, one_hour_offset)

    nose.tools.ok_(
        utc_datetime_back == utc_datetime)

    # NAIVE DATETIME
    naive_datetime = datetime.datetime(
        year=2014, month=5, day=4, hour=13, minute=0)
    utc_datetime = l10n.instance.to_utc_tz(naive_datetime, one_hour_offset)
    nose.tools.ok_(utc_datetime.hour == 12)

    naive_datetime = datetime.datetime(
        year=2014, month=5, day=4, hour=13, minute=0)
    user_datetime = l10n.instance.to_user_tz(naive_datetime, one_hour_offset)
    nose.tools.ok_(user_datetime.hour == 14)


def check_context():
    # DATETIME with TIMEZONE
    utc_offset = pytz.FixedOffset(0)
    utc_datetime = datetime.datetime.now(utc_offset)
    msk_offset = 60
    context = l10n.Context('en', msk_offset)

    localised_datetime = context.to_user_tz(utc_datetime)

    nose.tools.ok_(
        (localised_datetime - utc_datetime) == datetime.timedelta())

    # NAIVE DATETIME
    naive_datetime = datetime.datetime(
        year=2014, month=5, day=4, hour=13, minute=0)
    utc_datetime = context.to_utc_tz(naive_datetime)
    nose.tools.ok_(utc_datetime.hour == 12)

    naive_datetime = datetime.datetime(
        year=2014, month=5, day=4, hour=13, minute=0)
    user_datetime = context.to_user_tz(naive_datetime)
    nose.tools.ok_(user_datetime.hour == 14)
