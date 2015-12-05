# -*- coding: utf-8 -*-
"""
Демонизация, фоновый процесс
----------------------------

Для демонизации используется двойной fork.

Параметры настроек:
* daemonise Bool - переводить в фоновый процесс
* pid str - путь до файла с номер процесса
* uid/gid int - идентификатор пользователя/группы, от имени которого будет запущен демон
* umask oct - маска процесса
* chdir str - рабочая папка процесса
* stdin/stdout/stderr str - пути для перенаправления потоков вывода процесса

Настройки по умолчанию::

    {
        'daemonise': False,
        'pid': '/var/run/%s.pid' % name,
        'uid': None,
        'gid': None,
        'umask': None,
        'chdir': None,
        'stdin': None,
        'stdout': None,
        'stderr': None,
    }

Использование::

    class DaemonA(services.Daemon):
        def __init__(self):
            super(DaemonA, self).__init__(
                "daemona", "daemon.deamon_name", daemonise=True, pid=PID_PATH)

        def run(self):
            time.sleep(10)

    daemon = DaemonA()

    daemon.start()
    daemon.is_running()
    daemon.stop()
"""
import os
import sys
import signal
import logging
import time
import errno

from setproctitle import setproctitle

from ..config import Proxy
from ..utils import bcolors, colored_text


__all__ = ('Daemon', 'main',)


class Daemon(object):
    """
    Демон
    """

    def __init__(self, name, config_namespace, **config):
        """
        Конструктор

        :param str name: название процесса
        :param str config_namespace: префикс для файла настроек
        :param dict config: значения настроек по умолчанию
        """
        super(Daemon, self).__init__()
        default_config = {
            'daemonise': False,
            'pid': '/var/run/%s.pid' % name,
            'uid': None,
            'gid': None,
            'umask': None,
            'chdir': None,
            'stdin': None,
            'stdout': None,
            'stderr': None,
        }
        default_config.update(config)
        self.config = Proxy(default_config, config_namespace)
        self.name = name
        self.exit_code = None

    def start(self):
        """
        Запуск демона

        :return: Bool
        """
        if not self.config['daemonise']:
            print colored_text("Daemonisation disabled", bcolors.WARNING)
            self.run()
            return True
        if self.is_running():
            print colored_text(
                "Service already running [%d]" % self.pid, bcolors.WARNING)
            return True

        # first fork
        try:
            pid = os.fork()
            if pid > 0:
                for i in range(3):
                    if self.is_running():
                        print colored_text(
                            "Service started with pid {}".format(self.pid),
                            bcolors.OKGREEN
                        )
                        return True
                    time.sleep(1)
                return False
        except OSError as e:
            logging.error("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
            print colored_text(
                "fork #1 failed: %d (%s)\n" % (e.errno, e.strerror),
                bcolors.FAIL)
            return False
        except Exception, exc:
            logging.exception("fork #1 failed.")
            print colored_text(
                "fork #1 failed: %s\n" % (str(exc),), bcolors.FAIL)
            return False

        logging.info("#1 [%s] fork success", os.getpid())

        try:
            if self.config.get('chdir', None):
                os.chdir(self.config['chdir'])
                logging.info(
                    "[%s] chdir %s",
                    os.getpid(), self.config['chdir'])
            os.setsid()
            if self.config.get('umask', None):
                umask = int(self.config['umask'], base=8)
                os.umask(umask)
                logging.info(
                    "[%s] umask %s",
                    os.getpid(), self.config['umask']
                )
        except:
            logging.exception("Env configuration fail")
            os._exit(1)

        # second fork
        try:
            pid = os.fork()
            if pid > 0:
                os._exit(0)
        except OSError as e:
            logging.error("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
            os._exit(2)
        except Exception, exc:
            logging.exception("fork #2 failed.")
            os._exit(2)

        logging.info("#2 [%s] fork success", os.getpid())

        setproctitle(self.process_name)

        try:
            if self.config.get('stdin', None):
                si = file(self.config['stdin'], 'r')
                os.dup2(si.fileno(), sys.stdin.fileno())
                logging.info(
                    "[%s] stdin redirected to %s",
                    os.getpid(), self.config['stdin']
                )
            if self.config.get('stdout', None):
                sys.stdout.flush()
                so = file(self.config['stdout'], 'a+')
                os.dup2(so.fileno(), sys.stdout.fileno())
                logging.info(
                    "[%s] stdout redirected to %s",
                    os.getpid(), self.config['stdout']
                )
            if self.config.get('stderr', None):
                sys.stderr.flush()
                se = file(self.config['stderr'], 'a+', 0)
                os.dup2(se.fileno(), sys.stderr.fileno())
                logging.info(
                    "[%s] stderr redirected to %s",
                    os.getpid(), self.config['stderr']
                )
        except:
            logging.exception("std streams duplication fail")
            os._exit(3)

        if not self.write_pid():
            os._exit(4)

        if self.config.get('gid', None):
            os.setgid(self.config['gid'])
            logging.info(
                "[%s] group id %s",
                os.getpid(), self.config['gid']
            )
        if self.config.get('uid', None):
            os.setuid(self.config['uid'])
            logging.info(
                "[%s] user id %s",
                os.getpid(), self.config['uid']
            )

        exit_code = 0
        try:
            logging.info("[%s] Service started", os.getpid())
            self.run()
        except KeyboardInterrupt:
            logging.info("Service interupted by Ctrl+C")
        except SystemExit as e:
            exit_code = e.code
        except Exception as e:
            logging.exception(
                "Daemonized handler throw exception. Stopping daemon.")
            exit_code = 1
        finally:
            if self.pid == os.getpid():
                if os.path.exists(self.config['pid']):
                    os.remove(self.config['pid'])
        os._exit(exit_code)

    def stop(self):
        """
        Остановка демона

        :return: Bool
        """
        try:
            pid = self.pid
            if not pid:
                print colored_text("Service not started", bcolors.WARNING)
                return True
            while os.path.exists('/proc/%d/' % pid):
                try:
                    os.kill(int(pid), signal.SIGTERM)
                except OSError as err:
                    if err.errno == errno.ESRCH:
                        print colored_text(
                            "[%s] Stopped" % pid, bcolors.OKGREEN)
                    elif err.errno == errno.EPERM:
                        print colored_text(
                            "[%s] No permission to signal this process!" % pid,
                            bcolors.FAIL)
                    else:
                        print colored_text(
                            "[%s] Unknown error" % pid, bcolors.FAIL)
                    break
                time.sleep(0.5)
            if self.config.get('pid', None):
                if os.path.exists(self.config['pid']):
                    os.remove(self.config['pid'])
            if not os.path.exists('/proc/%d/' % pid):
                print colored_text("Service stopped", bcolors.OKGREEN)
                return True
        except OSError as e:
            if e.errno != 10:
                print e
        except Exception as e:
            print e
        return False

    def restart(self):
        """
        Рестарт демона

        :return: Bool
        """
        return self.stop() and self.start()

    def run(self):
        """
        Входная точка. Необходимо переопределить для каждого наследника.
        """
        raise NotImplementedError()

    def is_running(self):
        """
        Состояние демона (жив/мертв)

        :return: Bool
        """
        pid = self.pid
        if not pid:
            return False
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        else:
            return True

    def write_pid(self):
        if self.config.get('pid', None):
            try:
                fd = open(self.config['pid'], "w+")
                fd.write("%d" % os.getpid())
                fd.close()
                return True
            except:
                logging.exception(
                    "fail to save pid to [%s]", self.config['pid'])
        return False

    @property
    def pid(self):
        """
        Идентификатор процесса демона
        """
        if self.config.get('pid', None):
            if not os.path.exists(self.config['pid']):
                return None
            try:
                with open(self.config['pid'], "r") as fd:
                    return int(fd.read())
            except:
                logging.exception(
                    "fail to read pid file [%s]", self.config['pid']
                )
        return None

    @property
    def process_name(self):
        return "".join([i if i.split() else "-" for i in self.name.lower()])


commands = ["start", "stop", "restart", "status", "pid"]


def main(daemon, command=None):
    """
    Функция управления демоном

    :param object daemon: экземпляр класса
    :param str command: команда, по умолчанию start, доступны start/stop/restart/status/pid
    """
    if not command:
        command = 'start'
    if 'start' == command:
        if not daemon.start():
            print colored_text("Service start FAIL", bcolors.FAIL)
            sys.exit(1)
        sys.exit(0)
    elif 'stop' == command:
        if not daemon.stop():
            print colored_text("Service stop FAIL", bcolors.FAIL)
            sys.exit(1)
        sys.exit(0)
    elif 'restart' == command:
        if not daemon.restart():
            print colored_text("Service restart FAIL", bcolors.FAIL)
            sys.exit(1)
        sys.exit(0)
    elif 'status' == command:
        if daemon.is_running():
            print colored_text("Service is running", bcolors.OKGREEN)
        else:
            print colored_text("Service is down", bcolors.OKGREEN)
        sys.exit(0)
    elif 'pid' == command:
        if daemon.is_running():
            print colored_text(
                "Service pid is %d" % daemon.pid,
                bcolors.OKGREEN)
        else:
            print colored_text("Service is down", bcolors.OKGREEN)
        sys.exit(0)
    else:
        print colored_text("Action not define %s" % command, bcolors.FAIL)
