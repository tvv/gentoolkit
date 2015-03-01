# -*- coding: utf-8 -*-
"""
Пул экземпляров сервисов
------------------------

Класс `Pool` управляет набором экземпляров сервисов.

Задачи:
* запуск/остановка экземпляров сервиса
* перезапуск экземпляра при падении
* предоставление отчетности о состоянии экземпляров сервиса по сети

При реализации необходимо учитывать:
* сигналы SIGTERM и SIGCHLD не могут быть использованы
* системные вызовы могут быть прерваны сигналами
* сигналы установленные раннее не изменяются

Формат отчета::

    {
        'success': bool,
        'instances': {
            'serviceA-1': {
                'pid': int,
                'stopped': bool,
                'handler': str,
                'name': str,
                'report': instance_relate_data
            },
            ....
        }
    }

Пример использования::

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

    serviceA = services.Service("serviceA", Handler())
    serviceB = services.Service("serviceB", Handler())

    pool = services.Pool("pool.handler_name")
    pool.attach(serviceA)
    pool.attach(serviceB, 3)

    pool.serve()


Пример настроек::

    {
        "pool": {
            "handler_name": {
                "report": {
                    // адрес для внутреннего обмена между процессами
                    "incoming": ["127.0.0.1", 8881],
                    // внешний адрес доступа к отчетам
                    "outgoing": ["127.0.0.1", 8880]
                }
            }
        }
    }
"""
import logging
import signal
import errno
import socket
import json
import time

from ..config import Proxy


class Pool(object):
    """
    Пул экземпляров сервисов
    """
    def __init__(self, config_namespace=None):
        """
        Конструктор
        """
        super(Pool, self).__init__()
        # список закрепленных сервисов и требуемое количество экземпляров
        # [ {'service': object, 'multiply': int} ]
        # service - объект сервиса
        # multiple - количество экземпляров
        self.__services = []

        # список запущенных экземпляров
        self.__instances = []

        # флаг состояния
        self.__stopped = False

        # настройки пула
        self.config = Proxy({}, config_namespace or "_unset")

    def attach(self, service, multiply=None):
        """
        Добавления сервисов в пул

        :param object service: объект сервиса
        :param unt multiply: количество экземпляров, по умолчанию 1
        """
        if not multiply:
            logging.info("Service [%s] disabled", service.name)

        if "report" in self.config:
            service.report_addr = self.config['report']['incoming']

        self.__services.append({
            'service': service,
            'multiply': multiply
        })

    def start(self):
        """
        Запуск экземпляров

        :return: Bool
        """
        self.__stopped = False
        signal.signal(signal.SIGCHLD, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        try:
            for service in self.__services:
                if service['multiply']:
                    for i in range(service['multiply']):
                        instance = service['service'].start()
                        if not instance:
                            self.stop()
                            return False
                        self.__instances.append(instance)
            return True
        except:
            logging.exception("Fail to start pool")
            self.stop()
            return False

    def stop(self):
        """
        Остановка экземпляров

        :return: Bool
        """
        self.__stopped = True
        for instance in self.__instances:
            instance.stop()
        return True

    def restart(self):
        """
        Перезапуск экземпляров

        :return: Bool
        """
        return self.stop() and self.start()

    def instances(self):
        """
        Список запущенных экземпляров. Возвращает словарь, в ключ - название сервиса, значение - список экземпляров.

        :return: dict
        """
        ret = {}
        for service in self.__services:
            ret[service['service'].name] = service['service'].instances()
        return ret

    def signal_handler(self, sig, frame):
        """
        Обработчик сигналов
        """
        if sig == signal.SIGCHLD and not self.__stopped:
            for instance in self.__instances:
                pid = instance.pid
                if not instance.is_running() and not self.__stopped:
                    logging.info(
                        'Instance %s:%s died',
                        instance.name, instance.pid
                    )
                    if instance.exit_code == 0:
                        logging.info(
                            "Service [%s] finished normaly (exit_code=0), not restarting",
                            pid)
                    else:
                        logging.info(
                            "Child process [%d] exit with status code [%s]",
                            pid, str(instance.exit_code))
                        instance.start()
            if all([not i.is_running() for i in self.__instances]) and not self.__stopped:
                logging.info(
                    "All service instances stopped normaly. Stopping.")
                self.stop()
        if sig == signal.SIGTERM:
            self.stop()

    def serve(self):
        """
        Старт диспетчера пула сервисов. Если в конфигурации указаны настройки получения отчетов, стартует с интерфейсом отчетов.
        """
        if "report" in self.config:
            return self.serve_with_report(
                self.config['report']['outgoing'],
                self.config['report']['incoming'])
        else:
            logging.warning("Reporting disabled")
            return self.serve_blocking()

    def serve_blocking(self):
        """
        Старт диспетчера пула сервиса без отчетности. Блокирует выполнение в  месте вызова.
        """
        self.start()
        while not self.__stopped:
            try:
                signal.pause()
            except KeyboardInterrupt:
                self.__stopped = True
                self.stop()
            except (IOError, OSError) as e:
                if e.errno not in (errno.EINTR,):
                    logging.exception("Pause broken")
                    self.stop()
            except:
                logging.exception("Pause broken")
                self.stop()

    def serve_with_report(self, outgoing_addr, incoming_addr):
        """
        Старт диспетчера пула сервиса с возможностью получить отчет о состоянии экземпляров по сети. Блокирует выполнение в  месте вызова.

        :param tuple outgoing_addr: адрес, с которого можно получить отчет
        :param tuple incoming_addr: адрес, на который будут приходить отчеты от экземаляров сервисов
        """
        logging.info("Report avaliable at %s:%s", *outgoing_addr)
        logging.info(
            "Internal report iface avaliable at %s:%s", *incoming_addr
        )
        outgoing_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        outgoing_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        outgoing_sock.bind(tuple(outgoing_addr))
        outgoing_sock.listen(10)
        self.start()
        self.__started_at = int(time.time())
        while not self.__stopped:
            try:
                client, addr = outgoing_sock.accept()
                report = self.collect_reports(incoming_addr)
                while report:
                    send = client.send(report)
                    report = report[send:]
                client.close()
                logging.info("%s status reported", addr)
            except KeyboardInterrupt:
                self.stop()
            except (IOError, OSError) as e:
                if e.errno not in (errno.EINTR,):
                    logging.exception("Reporting is broken")
                    self.stop()
            except:
                logging.exception("Reporting is broken")
                self.stop()
        outgoing_sock.close()

    def collect_reports(self, incoming_addr):
        """
        Внутренний метод для сбора отчетности от экземпляр сервисов.

        Метод открывает сокет, последовательно вызывает метод `report` у каждого экземпляра и ожидает отчет.

        :param tuple incoming_addr: адрес, на который будут приходить отчеты от экземаляров сервисов

        :return: dict
        """
        try:
            incoming_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            incoming_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            incoming_sock.bind(tuple(incoming_addr))
            incoming_sock.settimeout(0.5)
            incoming_sock.listen(20)
            report = {
                'started_at': time.strftime(
                    "%d.%m.%Y %H:%M:%S "+time.tzname[0],
                    time.localtime(self.__started_at)
                ),
                'online': int(time.time()) - self.__started_at,
                'success': True,
                'instances_count': len(self.__instances),
                'instances': {}
            }
            for instance in self.__instances:
                if instance.report():
                    try:
                        client, addr = incoming_sock.accept()
                        report_data = ""
                        while 1:
                            chunk = client.recv(4096)
                            if not chunk:
                                break
                            report_data += chunk
                        report['instances'][instance.name] = json.loads(
                            report_data)
                    except socket.timeout:
                        logging.error(
                            "Waiting report from %s:%s timeout",
                            instance.name, instance.pid)
            incoming_sock.close()
            return json.dumps(report)
        except:
            logging.exception("Fail to collect reports")
            incoming_sock.close()
            return json.dumps({'success': False})
