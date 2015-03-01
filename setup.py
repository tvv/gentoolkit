# -*- coding: utf-8 -*-

from setuptools import setup


packages = [
    'gentoolkit',
    'gentoolkit.cache',
    'gentoolkit.config',
    'gentoolkit.extjson',
    'gentoolkit.l10n',
    'gentoolkit.logger',
    'gentoolkit.manhole',
    'gentoolkit.models',
    'gentoolkit.profiler',
    'gentoolkit.services',
]


setup(
    name='gentoolkit',
    version='0.1',
    description='General ToolKit',
    url='https://github.com/tvv/gentoolkit',
    author="vt",
    author_email='vturchaninov@gmail.com',
    packages=packages,
    install_requires=[
        'arrow>=0.4.4',
        'Babel>=1.3',
        'pytz>=2014.9',
        'tornado>=4.0.2',
        'pylibmc>=1.3.0',
        'setproctitle>=1.1.8',
        'simplejson>=3.6.5'
    ],
    setup_requires=[
        'nose>=1.0'
    ],
    test_suite='nose.collector'
)
