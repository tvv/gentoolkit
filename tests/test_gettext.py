# -*- coding: utf-8 -*-
import os

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
    instance = l10n.instance

    # translation exists RU
    msg = instance.gettext("test", locale='ru', domain='messages')
    nose.tools.ok_(msg == u'ru: тест', u"expecting 'ru: тест' got '%s'" % msg)

    # translation exists EN
    msg = instance.gettext("test", locale='en', domain='messages')
    nose.tools.ok_(msg == u'en: test', u"expecting 'en: test' got '%s'" % msg)

    # fallback to default language
    msg = instance.gettext("test", locale='fr', domain='messages')
    nose.tools.ok_(msg == u'en: test', u"expecting 'en: test' got '%s'" % msg)

    # message not found
    msg = instance.gettext("notexists", locale='en', domain='messages')
    nose.tools.ok_(
        msg == u'notexists',
        u"expecting 'notexists' got '%s'" % msg)

    # domain not exists
    msg = instance.gettext("test", locale='ru', domain='notexists')
    nose.tools.ok_(msg == u'test', u"expecting 'test' got '%s'" % msg)

    # PLURAL
    # Russian 3 plural forms
    msg = instance.ngettext(
        "found %d error", "found %d errors", 1,
        locale='ru', domain='messages')
    nose.tools.ok_(
        msg == u'ru: найдена %d ошибка',
        u"expecting 'ru: найдена %%d ошибка' got '%s'" % msg)

    msg = instance.ngettext(
        "found %d error", "found %d errors", 2,
        locale='ru', domain='messages')
    nose.tools.ok_(
        msg == u'ru: найдено %d ошибки',
        u"expecting 'ru: найдено %%d ошибки' got '%s'" % msg)

    msg = instance.ngettext(
        "found %d error", "found %d errors", 10,
        locale='ru', domain='messages')
    nose.tools.ok_(
        msg == u'ru: найдено %d ошибок',
        u"expecting 'ru: найдено %%d ошибок' got '%s'" % msg)

    # English 2 plural forms
    msg = instance.ngettext(
        "found %d error", "found %d errors", 1,
        locale='en', domain='messages')
    nose.tools.ok_(
        msg == u'en: found %d error',
        u"expecting 'en: found %%d error' got '%s'" % msg)

    msg = instance.ngettext(
        "found %d error", "found %d errors", 2,
        locale='en', domain='messages')
    nose.tools.ok_(
        msg == u'en: found %d errors',
        u"expecting 'en: found %%d errors' got '%s'" % msg)


def check_context():
    # translation exists RU
    context = l10n.Context('ru', 0)
    msg = context.gettext("test", domain='messages')
    nose.tools.ok_(msg == u'ru: тест', u"expecting 'ru: тест' got '%s'" % msg)

    # translation exists EN
    context = l10n.Context('en', 0)
    msg = context.gettext("test", domain='messages')
    nose.tools.ok_(msg == u'en: test', u"expecting 'en: test' got '%s'" % msg)

    # fallback to default language
    context = l10n.Context('fr', 0)
    msg = context.gettext("test", domain='messages')
    nose.tools.ok_(msg == u'en: test', u"expecting 'en: test' got '%s'" % msg)

    # message not found
    context = l10n.Context('en', 0)
    msg = context.gettext("notexists", domain='messages')
    nose.tools.ok_(
        msg == u'notexists',
        u"expecting 'notexists' got '%s'" % msg)

    # domain not exists
    context = l10n.Context('ru', 0)
    msg = context.gettext("test", domain='notexists')
    nose.tools.ok_(msg == u'test', u"expecting 'test' got '%s'" % msg)

    # PLURAL
    # Russian 3 plural forms
    context = l10n.Context('ru', 0)
    msg = context.ngettext(
        "found %d error", "found %d errors", 1, domain='messages')
    nose.tools.ok_(
        msg == u'ru: найдена %d ошибка',
        u"expecting 'ru: найдена %%d ошибка' got '%s'" % msg)

    msg = context.ngettext(
        "found %d error", "found %d errors", 2, domain='messages')
    nose.tools.ok_(
        msg == u'ru: найдено %d ошибки',
        u"expecting 'ru: найдено %%d ошибки' got '%s'" % msg)

    msg = context.ngettext(
        "found %d error", "found %d errors", 10, domain='messages')
    nose.tools.ok_(
        msg == u'ru: найдено %d ошибок',
        u"expecting 'ru: найдено %%d ошибок' got '%s'" % msg)

    # English 2 plural forms
    context = l10n.Context('en', 0)
    msg = context.ngettext(
        "found %d error", "found %d errors", 1, domain='messages')
    nose.tools.ok_(
        msg == u'en: found %d error',
        u"expecting 'en: found %%d error' got '%s'" % msg)

    msg = context.ngettext(
        "found %d error", "found %d errors", 2, domain='messages')
    nose.tools.ok_(
        msg == u'en: found %d errors',
        u"expecting 'en: found %%d errors' got '%s'" % msg)
