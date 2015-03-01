# -*- coding: utf-8 -*-
"""
Обработчики
----------------

Каждый сервис представляет собой отдельный процесс и процесс-родитель, который может посылать управляющие сигналы.

При реализации обработчиков необходимо учитывать:
* сигналы SIGTERM и SIGUSR1 не могут быть использованы
* системные вызовы могут быть прерваны сигналами

Формат отчета::

    {
        'pid': int,
        'stopped': bool,
        'handler': str,
        'name': str,
        'report': instance_relate_data
    }

Пример::

    class HandlerA(services.Handler):
        def __init__(self):
            super(Handler, self).__init__()
            # флаг состояния
            self.stopped = False

        def start(self):
            stt = int(time.time())
            endt = stt + 60
            while not self.stopped:
                # sleep может быть прерван сигналами
                time.sleep(endt - int(time.time()))
                if int(time.time()) > endt:
                    break

        def stop(self):
            self.stopped = True

        def report(self):
            return {
                'status': 100
            }

    service = Service("serviceA", HandlerA(), ("127.0.0.1", 2000))

    instance = service.start()
    instance.is_running()
    instance.stop()
"""
import os
import signal
import logging
import time
import errno
import json
import socket

from setproctitle import setproctitle


__all__ = ('Service', 'Handler', 'WrongHandler')


CALLBACK_STATE_STARTED = 1
CALLBACK_STATE_STOPPED = 2


class WrongHandler(Exception):
    """
    Передан обработчик, который не наследует класс `Handler`.
    """


class Handler(object):
    """
    Базовый класс обработчика, данный класс вызывается в контексте порожденного процесса
    """

    def start(self):
        """
        Данный метод вызывается после старта дочернего процесса. Выход из этой функции завершает процесс.
        """
        raise NotImplementedError()

    def stop(self):
        """
        Вызывается при получении сигнала (SIGTERM) на завершение процесса. В данном методе необходимо реализовать алгоритм остановки сервиса.
        """
        raise NotImplementedError()

    def report(self):
        """
        Вызывается при формировании отчета, сигнал SIGUSR1. Метод должен возвращать стандартные структуры из библиотеки Python, которые могут быть сериализована в json (модуль json).
        """
        raise NotImplementedError()

    def start_manhole(self, addr, context={}):
        """
        Запустить Manhole на указанном адресе.
        """
        try:
            logging.debug("Manhole starting")
            from core.manhole import Telnet
            port = addr[1] + self.context.seq_number
            self.__manhole_telnet = Telnet(
                (addr[0], port), context, globals())
            logging.info(
                "Manhole avaliable at %s:%s",
                addr[0], port)
            return addr[0], port
        except:
            logging.exception("Manhole fail to start addr=%s", addr)
            return None

    def __unicode__(self):
        """
        Человеко-читаемое название обработчика, передается в отчете.
        """
        return self.__class__.__name__


class Context(object):
    """
    Контекст сервиса. Создается в порожденном процессе.

    Задачи:
    * обработка сигнала SIGTERM и SIGUSR1
    * сброс всех обработчиков сигнал на дефолтные
    * формирование и отправка отчета
    """
    def __init__(self, seq_number, name, handler, report_addr):
        """
        Конструктор

        :param str name: название сервиса
        :param object handler: обработчик, наследние `Handler`
        :param tuple report_addr: адрес для отправки отчетов ("host", port)
        """
        super(Context, self).__init__()
        self.__handler = handler
        self.__report_addr = report_addr
        self.__stopped = False
        self.__reset_signal_handlers()
        self.__started_at = 0
        self.name = name
        self.seq_number = seq_number
        self.pid = None

    def __reset_signal_handlers(self):
        """
        Сброс сигналов
        """
        for i in range(1, signal.NSIG):
            if signal.getsignal(i) not in (signal.SIG_DFL, None):
                signal.signal(i, signal.SIG_DFL)

    def start(self):
        """
        Запуск обработки
        """
        exit_code = 0
        self.pid = os.getpid()
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGUSR1, self.signal_handler)
        try:
            self.__handler.context = self
            self.__started_at = int(time.time())
            self.__handler.start()
        except:
            self.__handler.stop()
            logging.exception("Handling fail [%s]", self.pid)
            exit_code = 1
        self.__handler.context = None
        os._exit(exit_code)

    def signal_handler(self, sig, frame):
        """
        Обработчик сигналов
        """
        if sig == signal.SIGTERM:
            self.__handler.stop()
            self.__stopped = True
        if sig == signal.SIGUSR1:
            self.__send_report(self.__handler.report())

    def __send_report(self, report):
        """
        Отправка отчета на указанный адрес

        :param dict report: отчет
        """
        if not report:
            logging.warning("Report is empty [%s]", self.pid)
        if not self.__report_addr:
            logging.debug("Report address not defined [%s]", self.pid)
            return
        try:
            msg = json.dumps({
                'pid': self.pid,
                'stopped': self.__stopped,
                'started_at': time.strftime(
                    "%d.%m.%Y %H:%M:%S "+time.tzname[0],
                    time.localtime(self.__started_at)
                ),
                'online': int(time.time()) - self.__started_at,
                'handler': unicode(self.__handler),
                'name': self.name,
                'report': report
            })
            conn = socket.create_connection(self.__report_addr, 0.2)
            while msg:
                send = conn.send(msg)
                msg = msg[send:]
            conn.close()
        except socket.timeout:
            logging.error("Connection timeout %s", self.__report_addr)
        except:
            logging.exception("Report not sended")


class Instance(object):
    """
    Экземпляр сервиса.

    Возможности:
    * старт, остановка, перезапуск
    * проверка состояния (жив/мертв)
    * запрос на формирование отчета
    """
    def __init__(self, seq_number, name, handler, report_addr, callback):
        """
        Конструктор. Вызывается через метод `Service.start`

        :param str name: название экземпляра
        :param object handler: обработчик
        :param tuple report_addr: адрес для отправки отчетов
        :param func callback: функция обратного вызова (старт и остановка)
        """
        super(Instance, self).__init__()
        self.__pid = 0
        self.__seq_number = seq_number
        self.__name = name
        self.__handler = handler
        self.__report_addr = report_addr
        self.__callback = callback
        self.__reported_count = 0

        # статус выхода
        self.exit_code = None

    @property
    def pid(self):
        """
        Идентификатор процесса
        """
        return self.__pid

    @property
    def name(self):
        """
        Название процесса
        """
        return self.__name

    @property
    def proccess_name(self):
        return "".join([i if i.split() else "-" for i in self.name.lower()])

    @property
    def report_addr(self):
        """
        Адрес для отправки отчетов
        """
        return self.__report_addr

    @property
    def reported_count(self):
        """
        Количество запрошенных отчетов
        """
        return self.__reported_count

    @property
    def seq_number(self):
        """
        Номер инстанса
        """
        return self.__seq_number

    def start(self):
        """
        Старт сервиса

        :return: bool
        """
        try:
            pid = os.fork()
            if pid > 0:
                self.__pid = pid
                for i in range(3):
                    if self.is_running():
                        self.__callback(CALLBACK_STATE_STARTED, self)
                        return True
                    time.sleep(0.2)
                return False
            self.__pid = os.getpid()
        except:
            logging.exception("[%s] Fork failed.", self.__name)
            return False

        logging.info(
            "[%s] Fork success [%s]",
            self.__name, os.getpid())

        setproctitle(self.proccess_name)

        exit_code = 0
        try:
            logging.info(
                "[%s] Service started [%s]",
                self.__name, os.getpid())
            context = Context(
                self.seq_number, self.name, self.__handler, self.report_addr)
            context.start()
        except KeyboardInterrupt:
            logging.info(
                "[%s] Service interupted by Ctrl+C",
                self.__name)
        except SystemExit as e:
            exit_code = e.code
        except Exception as e:
            logging.exception(
                "[%s] Daemonized handler throw exception. Stopping daemon.",
                self.__name)
            time.sleep(0.1)
            exit_code = 1
        os._exit(exit_code)

    def stop(self):
        """
        Остановка сервиса

        :return: bool
        """
        if not self.is_running():
            logging.error(
                "[%s] Trying to stop not running process",
                self.__name)
            self.__pid = None
            self.__callback(CALLBACK_STATE_STOPPED, self)
            return True
        try:
            os.kill(self.pid, signal.SIGTERM)
            for i in range(10):
                if not self.is_running():
                    logging.info(
                        "[%s] Service stopped [%s]",
                        self.__name, self.pid)
                    self.__pid = None
                    self.__callback(CALLBACK_STATE_STOPPED, self)
                    return True
                time.sleep(0.5)
            logging.error(
                "[%s] Fail to stop service [%s]",
                self.__name, self.pid)
        except OSError as err:
            if err.errno == errno.ESRCH:
                pass
            elif err.errno == errno.EPERM:
                logging.error(
                    "[%s] No permission to signal this process [%s]!",
                    self.__name, self.pid)
            else:
                logging.exception(
                    "[%s] Unknown error [%s]", self.__name, self.pid)
        except:
            logging.exception(
                "[%s] Fail to stop service [%s]",
                self.__name, self.pid)
        return False

    def restart(self):
        """
        Рестарт сервиса

        :return: bool
        """
        return self.stop() and self.start()

    def report(self):
        """
        Запрос отчета

        :return: bool
        """
        if not self.is_running():
            logging.error(
                "[%s] Unable to report, [%s] service is down",
                self.__name, self.pid)
            return False
        if not self.report_addr:
            logging.debug(
                "[%s] Report address not defined [%s]",
                self.__name, self.pid)
            return False
        try:
            os.kill(self.pid, signal.SIGUSR1)
            self.__reported_count += 1
            return True
        except:
            logging.exception(
                "[%s] Fail to send kill(%s, %s)",
                self.__name, self.pid, signal.SIGUSR1)
        return False

    def is_running(self):
        """
        Состояние сервиса

        :return: bool
        """
        if self.pid:
            try:
                os.kill(self.pid, 0)
                pid, status = os.waitpid(self.pid, os.WNOHANG)
                if pid:
                    if os.WIFEXITED(status):
                        self.exit_code = os.WEXITSTATUS(status)
                    else:
                        self.exit_code = None
                    return False
                return True
            except OSError as err:
                if err.errno != errno.ESRCH:
                    logging.exception("Fail to send kill(%s, 0)", self.pid)
            except:
                logging.exception("Fail to send kill(%s, 0)", self.pid)
        return False


class Service(object):
    """
    Управление сервисами.

    Возможности:
    * запуск сервиса, получение экземпляра сервиса
    * информация о запущенных экземплярах
    """
    def __init__(self, name, handler, report_addr=None):
        """
        Конструктор

        :param str name: название
        :param object handler: обработчик
        :param tuple report_addr: адрес для отправки отчетов
        """
        super(Service, self).__init__()
        if not isinstance(handler, Handler):
            raise WrongHandler(
                "%s" % (repr(handler),))
        self.__name = name
        self.__handler = handler
        self.__report_addr = report_addr

        # последний порядковый номер экземпляра сервиса
        self.__seq_number = 0

        # список всех запущенных экземпляров
        self.__instances = []

    @property
    def report_addr(self):
        """
        Адрес для отправки отчетов
        """
        return self.__report_addr

    @report_addr.setter
    def report_addr(self, report_addr):
        self.__report_addr = tuple(report_addr)

    @property
    def name(self):
        """
        Название сервиса
        """
        return self.__name

    def start(self):
        """
        Запуск экземпляра класса, возвращает объект экземпляра класса или None.

        :return: None|Instance
        """
        self.__seq_number += 1
        name = "%s-%d" % (self.__name, self.__seq_number)
        instance = Instance(
            self.__seq_number, name, self.__handler,
            self.__report_addr, self.__callback)
        if instance.start():
            return instance
        return None

    def __callback(self, state, instance):
        if state == CALLBACK_STATE_STARTED:
            self.__instances.append(instance)
        elif state == CALLBACK_STATE_STOPPED:
            try:
                self.__instances.remove(instance)
            except:
                pass
        else:
            logging.error("Unknown state %s for callback", state)

    def instances(self):
        """
        Список запущенных экземпляров класса. Список состоит из словарей, которые содержат поля: pid, name, reported_count.
        """
        return [
            {
                'pid': i.pid,
                'name': i.name,
                'reported_count': i.reported_count
            } for i in self.__instances]
