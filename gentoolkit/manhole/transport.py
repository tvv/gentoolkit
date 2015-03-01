# -*- coding: utf-8 -*-
import logging

import tornado.tcpserver
import tornado.web

from .console import Console


class Telnet(tornado.tcpserver.TCPServer):
    """
    Telnet доступ к интерпретатору
    """
    def __init__(self, addr, locals_dct, globals_dct, *args, **kwargs):
        """
        Конструктор

        :param tuple addr: адрес (ip, port)
        :param dict locals_dct: локальный контекст интерпретатора
        :param dict globals_dct: глобальный контекст интерпретатора
        """
        super(Telnet, self).__init__(*args, **kwargs)
        self.locals = locals_dct
        self.globals = globals_dct
        try:
            self.listen(addr[1])
        except:
            logging.exception(
                "Manhole. Fail to bind address 0.0.0.0:%s", addr[1])
        self.sessions = []

    def handle_stream(self, stream, address):
        logging.info("Manhole connect %s", address)
        session = Session(
            stream, self.locals, self.globals, self.stream_closed, address)
        self.sessions.append(session)

    def stream_closed(self, session):
        logging.info("Manhole closed %s", session.address)
        self.sessions.remove(session)


class Session(Console):
    def __init__(self, stream, locals_dct, globals_dct, callback, address):
        super(Session, self).__init__(locals_dct, globals_dct)
        self.console = Console(locals_dct, globals_dct)
        self.address = address
        self.stream = stream
        self.callback = callback
        self.stream.set_close_callback(self.stream_closed)
        self.write()

    def write(self, data=None):
        if data:
            data += "\r\n>>> "
        else:
            data = ">>> "
        self.stream.write(data, callback=self.read)

    def read(self):
        if not self.stream.reading():
            self.stream.read_until("\r\n", callback=self.handle)

    def handle(self, data):
        if data.strip() in ("exit", "exit()"):
            self.stream.close()
        else:
            self.write(self.run(data))

    def stream_closed(self):
        callback = self.callback
        self.callback = None
        callback(self)


class Web(object):
    def __init__(self, addr, locals_dct, globals_dct):
        super(Web, self).__init__(locals_dct, globals_dct)
        self.addr = addr
        self.application = tornado.web.Application([
            (r"/_manhole", WebHandler,
                dict(locals_dct=locals_dct, globals_dct=globals_dct)),
        ])
        self.application.listen(addr[1])


class WebHandler(tornado.web.RequestHandler):
    def initialize(self, locals_dct, globals_dct):
        self.console = Console(locals_dct, globals_dct)

    def get(self):
        self.write("Hello, world")

    def post(self):
        cmd = self.get_body_argument('cmd', None)
        if cmd:
            self.write(self.console.run(cmd))
