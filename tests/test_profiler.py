# -*- coding: utf-8 -*-
import socket
import threading
import time

import nose.tools

from gentoolkit import Profiler
from gentoolkit import profile


ADDRESS = ('127.0.0.1', 2004)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(ADDRESS)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.settimeout(0.5)


class Acceptor(threading.Thread):

    """
    Graphite service mock. Listen UDP socket at 127.0.0.1:2004. All accepted message stored in `Acceptor.accepted` list.
    """
    accepted = []
    stopped = False

    def run(self):
        self.accepted = []
        self.stopped = False
        while True:
            try:
                data, addr = sock.recvfrom(1024)
                name, value, tm = data.split(" ")
                self.accepted.append((name, value, int(tm)))
            except socket.timeout:
                if self.stopped:
                    break

    def stop(self):
        """
        Stop accepting
        """
        self.stopped = True


hostname = socket.gethostname()


def test_profiler():
    check_profiler()
    check_profiler_context()
    check_profiler_context_with_exc()
    check_timer_context()
    check_decorator()


def check_profiler():
    """
    Добавление метрик вручную через метод `Profiler.append`.
    """
    acceptor = Acceptor()
    acceptor.start()
    time.sleep(0.5)

    profiler_inst = Profiler()
    profiler_inst.append("name1", 1)
    profiler_inst.append("name2", 2)
    profiler_inst.append("name3", 3)
    profiler_inst.flush()

    time.sleep(0.5)
    acceptor.stop()

    nose.tools.ok_(len(acceptor.accepted) == 4, acceptor.accepted)

    message_value = {
        '%s.name1' % hostname: '1',
        '%s.name2' % hostname: '2',
        '%s.name3' % hostname: '3'
    }
    avg_found = False

    for msg in acceptor.accepted:
        if msg[0] == "%s.avg" % hostname:
            avg_found = True
        else:
            nose.tools.ok_(
                msg[0] in message_value,
                "%s and %s" % (msg[0], message_value)    
            )
            nose.tools.ok_(msg[1] == message_value[msg[0]])
    nose.tools.ok_(avg_found)


def check_profiler_context():
    """
    Использование контекста класса Profiler
    """
    acceptor = Acceptor()
    acceptor.start()
    time.sleep(0.5)

    with Profiler() as p:
        p.append("name1", 1)
        p.append("name2", 2)

    time.sleep(0.5)
    acceptor.stop()

    nose.tools.ok_(len(acceptor.accepted) == 3, acceptor.accepted)

    msgs = {i[0]: i for i in acceptor.accepted}
    nose.tools.ok_(int(msgs['%s.name1' % hostname][1]) == 1)


def check_profiler_context_with_exc():
    """
    Исключения в контексте профейлера не скрываются, собранные метрики нормально уходят на сервер.
    """
    acceptor = Acceptor()
    acceptor.start()
    time.sleep(0.5)

    try:
        with Profiler() as p:
            p.append("name1", 1)
            raise Exception()
            p.append("name2", 2)
    except:
        pass

    time.sleep(0.5)
    acceptor.stop()

    nose.tools.ok_(len(acceptor.accepted) == 2, acceptor.accepted)

    msgs = {i[0]: i for i in acceptor.accepted}
    nose.tools.ok_(int(msgs['%s.name1' % hostname][1]) == 1)


def check_timer_context():
    """
    Контекст таймера
    """
    acceptor = Acceptor()
    acceptor.start()
    time.sleep(0.5)

    profiler_inst = Profiler()
    with profiler_inst.begin('name1'):
        time.sleep(1)
    profiler_inst.flush()

    time.sleep(0.5)
    acceptor.stop()

    nose.tools.ok_(len(acceptor.accepted) == 2, acceptor.accepted)

    msgs = {i[0]: i for i in acceptor.accepted}
    nose.tools.ok_(float(msgs['%s.name1' % hostname][1]) >= 1)


def check_decorator():
    """
    Использование декоратора
    """
    acceptor = Acceptor()
    acceptor.start()
    time.sleep(0.5)

    @profile("func")
    def func(sleep):
        time.sleep(sleep)

    func(1)

    time.sleep(0.5)
    acceptor.stop()

    nose.tools.ok_(len(acceptor.accepted) == 1, acceptor.accepted)

    msgs = {i[0]: i for i in acceptor.accepted}
    nose.tools.ok_(float(msgs['%s.func.avg' % hostname][1]) >= 1)
