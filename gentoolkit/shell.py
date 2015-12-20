# -*- coding: utf-8 -*-

import argh
import argh.decorators

from rng_core import services
from rng_core.config import init as init_config
from rng_core.logger import init as init_logger


def get_service_command(daemon_class, logger_name):

    @argh.decorators.arg(
        "command", choices=["start", "stop", "restart", "status"],
        help="service command")
    @argh.decorators.arg(
        "-c", "--config", help="configuration file path")
    def service(command, config="local.json"):
        """
        manage daemon
        """
        init_config(config)
        init_logger(logger_name)
        services.daemon.main(daemon_class(), command)
    return service


def get_shell_command(logger_name):

    @argh.decorators.arg(
        "-c", "--config", help="configuration file path")
    def shell(config="local.json"):
        """
        interactive shell
        """
        init_config(config)
        init_logger(logger_name)

        import code
        import readline
        import rlcompleter
        import atexit
        import os

        historyPath = os.path.expanduser("~/.pyhistory")

        def save_history(historyPath=historyPath):
            import readline
            readline.write_history_file(historyPath)

        if os.path.exists(historyPath):
            readline.read_history_file(historyPath)

        atexit.register(save_history)

        vars = globals()
        vars.update(locals())
        readline.set_completer(rlcompleter.Completer(vars).complete)
        readline.parse_and_bind("tab: complete")
        shell = code.InteractiveConsole(vars)
        shell.interact()
    return shell


def dispatch(daemon_class, logger_name, *args):
    argh.dispatch_commands(
        [
            get_service_command(daemon_class, logger_name),
            get_shell_command(logger_name),
        ] + list(args)
    )
