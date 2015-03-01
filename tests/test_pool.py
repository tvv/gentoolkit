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


INCOMING_ADDR = ("127.0.0.1", 2001)
OUTGOING_ADDR = ("127.0.0.1", 2000)


class Handler(services.Handler):
    def __init__(self):
        super(Handler, self).__init__()
        self.stopped = False

    def start(self):
        stt = int(time.time())
        endt = stt + 60
        while not self.stopped:
            if int(time.time()) > endt:
                break
            time.sleep(endt - int(time.time()))

    def stop(self):
        self.stopped = True

    def report(self):
        return {
            'status': 100
        }


class ReportClient(threading.Thread):

    """
    Report client moc
    """
    report = None

    def run(self):
        try:
            conn = socket.create_connection(OUTGOING_ADDR, 0.2)
            data = ""
            while 1:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                data += chunk
            self.report = json.loads(data)
        except:
            pass


def test_pool_start_stop():
    logger.init("test_pool", debug=False, stdout=True)

    serviceA = services.Service("serviceA", Handler())
    serviceB = services.Service("serviceB", Handler(), INCOMING_ADDR)

    pool = services.Pool()
    pool.attach(serviceA)
    pool.attach(serviceB, 3)

    pool.start()
    time.sleep(1)

    instances = pool.instances()
    nose.tools.ok_('serviceA' in instances)
    nose.tools.ok_('serviceB' in instances)
    nose.tools.ok_(len(instances['serviceA']) == 0)
    nose.tools.ok_(len(instances['serviceB']) == 3)

    pool.stop()


def test_pool_serve():
    serviceA = services.Service("serviceA", Handler())
    serviceB = services.Service("serviceB", Handler(), INCOMING_ADDR)

    pool = services.Pool()
    pool.attach(serviceA, 1)
    pool.attach(serviceB, 3)

    def signal_handler(sig, frame):
        pool.stop()

    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(2)

    pool.serve()


def test_pool_serve_restart_instance():
    serviceA = services.Service("serviceA", Handler())
    serviceB = services.Service("serviceB", Handler(), INCOMING_ADDR)

    pool = services.Pool()
    pool.attach(serviceA, 1)
    pool.attach(serviceB, 3)

    prev_pid = None

    def signal_handler_kill_instance(sig, frame):
        global prev_pid
        instances = pool.instances()
        prev_pid = instances['serviceA'][0]['pid']
        os.kill(prev_pid, signal.SIGKILL)
        signal.signal(signal.SIGALRM, signal_handler)
        signal.alarm(2)

    def signal_handler(sig, frame):
        instances = pool.instances()
        nose.tools.ok_(prev_pid != instances['serviceA'][0]['pid'])
        pool.stop()

    signal.signal(signal.SIGALRM, signal_handler_kill_instance)
    signal.alarm(2)

    pool.serve()


def test_pool_serve_with_report():
    serviceA = services.Service("serviceA", Handler())
    serviceB = services.Service("serviceB", Handler(), INCOMING_ADDR)

    pool = services.Pool()
    pool.attach(serviceA)
    pool.attach(serviceB, 3)

    report_client = ReportClient()

    def get_report(sig, frame):
        report_client.start()
        signal.signal(signal.SIGALRM, signal_handler)
        signal.alarm(2)

    def signal_handler(sig, frame):
        nose.tools.ok_(len(report_client.report['instances']) == 3)
        pool.stop()

    signal.signal(signal.SIGALRM, get_report)
    signal.alarm(2)

    pool.serve_with_report(OUTGOING_ADDR, INCOMING_ADDR)
