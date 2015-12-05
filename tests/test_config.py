# -*- coding: utf-8 -*-
import os
import json

import nose.tools

from gentoolkit import config


root_path = os.path.abspath(
    os.path.dirname(__file__)
)


cfg = {
    "param1": 1,
    "param2": "string",
    "param3": {
        "nest1": True,
        "nest2": [1, 2, 3]
    },
    "param4": {
        "nest1": [
            {
                "list1": 1,
                "list2": 2
            },
            1,
            "string"
        ]
    }
}


cfg_path = os.path.join("/tmp", "gentoolkit_config_test.json")


def setup():
    with open(os.path.join(root_path, cfg_path), "w+") as fd:
        fd.write(
            json.dumps(cfg)
        )


def teardown():
    os.unlink(cfg_path)


def test_uninitialised():
    instance = config.Config()
    with nose.tools.assert_raises(AttributeError):
        instance.get('param1')

    with nose.tools.assert_raises(AttributeError):
        instance.get('param3.nest1')

    nose.tools.ok_(1 == instance.get('param1', 1))
    nose.tools.ok_(instance.get('param3.nest1', True))

    with nose.tools.assert_raises(AttributeError):
        instance['param1']

    with nose.tools.assert_raises(AttributeError):
        instance[0]

    nose.tools.ok_(0 == len(instance))
    nose.tools.ok_(False == ('param1' in instance))


def test_initialised():
    def test_access(instance):
        nose.tools.ok_(True == ('param1' in instance))
        nose.tools.ok_(True == ('param3.nest1' in instance))
        nose.tools.ok_(False == ('param1.nest1' in instance))
        nose.tools.ok_(0 < len(instance))

        with nose.tools.assert_raises(AttributeError):
            instance.get('param100')

        nose.tools.ok_(1 == instance.get('param1'))
        nose.tools.ok_(instance.get('param3.nest1'))

    instance = config.Config()
    instance.init(cfg_path)
    test_access(instance)

    instance = config.Config()
    instance.init(cfg)
    test_access(instance)


def test_proxy_uninitialised():
    instance = config.Config()
    local_cfg = config.Proxy(
        {
            'nest1': 'default',
            'nest4': 'default'
        },
        'param3',
        config=instance
    )

    with nose.tools.assert_raises(AttributeError):
        local_cfg['nest2']

    with nose.tools.assert_raises(AttributeError):
        local_cfg.get('nest2')

    nose.tools.ok_('default' == local_cfg['nest1'])
    nose.tools.ok_('default' == local_cfg['nest4'])
    nose.tools.ok_('nest4' in local_cfg)


def test_proxy_initialised():
    instance = config.Config()
    instance.init(cfg_path)
    local_cfg = config.Proxy(
        {
            'nest1': 'default',
            'nest4': 'default'
        },
        'param3',
        config=instance
    )

    with nose.tools.assert_raises(AttributeError):
        local_cfg['nest5']

    with nose.tools.assert_raises(AttributeError):
        local_cfg.get('nest5')

    nose.tools.ok_(local_cfg['nest1'])
    nose.tools.ok_(1 == local_cfg['nest2'][0])
    nose.tools.ok_('default' == local_cfg['nest4'])
