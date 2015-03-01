# -*- coding: utf-8 -*-

import socket
import threading
import time
import logging
import json
import signal
import os

import nose.tools

from gentoolkit import services
from gentoolkit import logger


PID_PATH = "/tmp/daemonA.pid"


class DaemonA(services.Daemon):
    def __init__(self):
        super(DaemonA, self).__init__(
            "daemona", "daemona", daemonise=True, pid=PID_PATH)

    def run(self):
        time.sleep(10)


def test_deaemon():
    logger.init("test_deaemon", debug=False, stdout=True)
    daemon = DaemonA()
    nose.tools.ok_(daemon.start())
    nose.tools.ok_(daemon.is_running())
    nose.tools.ok_(os.path.exists(PID_PATH))
    nose.tools.ok_(daemon.stop())

    nose.tools.ok_(not daemon.is_running())
    nose.tools.ok_(not os.path.exists(PID_PATH))
