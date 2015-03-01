# -*- coding: utf-8 -*-

import socket
import threading
import time
import logging
import json

import nose.tools

from gentoolkit import services

INCOMING_ADDR = ("127.0.0.1", 2001)
OUTGOING_ADDR = ("127.0.0.1", 2000)

incoming_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
incoming_sock.bind(INCOMING_ADDR)
incoming_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
incoming_sock.settimeout(0.5)
incoming_sock.listen(10)


class Acceptor(threading.Thread):

    """
    Report acceptor moc
    """
    accepted = []
    stopped = False

    def run(self):
        self.accepted = []
        self.stopped = False
        while True:
            try:
                sock, addr = incoming_sock.accept()
                if sock:
                    data = ""
                    while 1:
                        chunk = sock.recv(4096)
                        if not chunk:
                            break
                        data += chunk
                    sock.close()
                    self.accepted.append(data)
            except socket.timeout:
                if self.stopped:
                    break

    def stop(self):
        """
        Stop accepting
        """
        self.stopped = True


class Handler(services.Handler):
    def __init__(self):
        super(Handler, self).__init__()
        self.stopped = False

    def start(self):
        stt = int(time.time())
        endt = stt + 60
        while not self.stopped:
            time.sleep(endt - int(time.time()))
            if int(time.time()) > endt:
                break

    def stop(self):
        self.stopped = True

    def report(self):
        return {
            'status': 100
        }


def test_service_without_report():
    service = services.Service("name1", Handler())
    instance = service.start()

    nose.tools.ok_(instance is not None)
    nose.tools.ok_(instance.is_running())
    nose.tools.ok_(instance.pid)

    nose.tools.ok_(not instance.report())
    nose.tools.ok_(instance.reported_count == 0)
    nose.tools.ok_(instance.is_running())

    instances = service.instances()
    nose.tools.ok_(instances[0]['pid'] == instance.pid)
    nose.tools.ok_(instances[0]['name'] == instance.name)
    nose.tools.ok_(instances[0]['reported_count'] == instance.reported_count)

    time.sleep(1)
    nose.tools.ok_(instance.stop())
    nose.tools.ok_(not instance.is_running())

    instances = service.instances()
    nose.tools.ok_(len(instances) == 0)


def test_service_with_report():
    acceptor = Acceptor()
    service = services.Service("name1", Handler(), INCOMING_ADDR)
    instance = service.start()

    nose.tools.ok_(instance is not None)
    nose.tools.ok_(instance.is_running())
    nose.tools.ok_(instance.pid)

    acceptor.start()
    time.sleep(1)
    pid = instance.pid

    nose.tools.ok_(instance.report())
    nose.tools.ok_(instance.reported_count > 0)
    nose.tools.ok_(instance.is_running())

    time.sleep(1)

    instances = service.instances()
    nose.tools.ok_(instances[0]['pid'] == pid)
    nose.tools.ok_(instances[0]['name'] == instance.name)
    nose.tools.ok_(instances[0]['reported_count'] == instance.reported_count)

    time.sleep(1)
    nose.tools.ok_(instance.stop())
    nose.tools.ok_(not instance.is_running())

    acceptor.stop()
    nose.tools.ok_(len(acceptor.accepted) == 1)

    msg = json.loads(acceptor.accepted[0])
    nose.tools.ok_(msg['pid'] == pid, msg)
    nose.tools.ok_(not msg['stopped'], msg)
    nose.tools.ok_(msg['name'] == 'name1-1', msg)
    nose.tools.ok_(msg['report']['status'] == 100, msg)
