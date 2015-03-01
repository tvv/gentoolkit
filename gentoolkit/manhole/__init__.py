# -*- coding: utf-8 -*-
"""
Manhole (доступ к интерпретатору процесса)
------------------------------------------
"""

from .transport import Telnet, Web


__all__ = ['Telnet', 'Web']
