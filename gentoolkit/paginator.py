# -*- coding: utf8 -*-
"""
Пагинация
=============
"""

import math


class Paginator(object):
    PAGE_ARG = "page"
    PER_PAGE_ARG = "perpage"

    def __init__(self, request, count, **kwargs):
        super(Paginator, self).__init__()
        self.request = request
        self.page_arg = \
            kwargs.get('page_arg', None) or self.PAGE_ARG
        self.per_page_arg = \
            kwargs.get('per_page_arg', None) or self.PER_PAGE_ARG
        self.page_window = kwargs.get('page_window', 5)
        self.default_per_page = kwargs.get('default_per_page', 20)
        self.page = 1
        self.per_page = self.default_per_page
        self.count = count or 0
        self.pages = 0
        self.path = kwargs.get('path', '') or ""

        try:
            page = self.request.get(self.page_arg, None)
            if isinstance(page, (list, tuple)):
                page = page[0]
            self.page = int(page)
        except:
            pass
        try:
            per_page = self.request.get(self.per_page_arg, None)
            if isinstance(per_page, (list, tuple)):
                per_page = per_page[0]
            self.per_page = int(per_page)
        except:
            pass
        self.pages = int(math.ceil(float(self.count) / self.per_page))
        if self.page > self.pages:
            self.page = self.pages

    @property
    def page_range(self):
        """
        Возвращает список номеров страниц.
        """
        if self.count == 0:
            return []
        max_pages = self.page_window * 4
        if self.pages <= max_pages:
            return range(1, self.pages + 1)
        else:
            page_window = self.page_window
            head = range(1, page_window + 1)
            tail = range(self.pages - page_window, self.pages + 1)
            appendix = int(math.ceil(self.page_window / 2))
            middle_page = self.pages / 2
            middle = range(middle_page - appendix, middle_page + appendix + 1)

            start = self.page - appendix
            if start <= self.page_window:
                start = self.page_window + 1
            end = self.page + appendix
            if end >= self.pages - self.page_window:
                end = self.pages - self.page_window - 1
            middle = range(start, end + 1)

            if middle and head[-1] + 1 >= middle[0]:
                head += middle
                middle = None
            if middle and middle[-1] + 1 >= tail[0]:
                tail = middle + tail
                middle = None
            if head[-1] + 1 >= tail[0]:
                return head + tail
            if middle:
                return head + [-1] + middle + [-1] + tail
            if self.pages / page_window > 4:
                l = len(head) + len(tail) - page_window * 2
                l = page_window - l + 1
                if l <= 0:
                    l = 1
                middle = range(middle_page, middle_page + l)
            return head + [-1] + middle + [-1] + tail

    @property
    def begin(self):
        """
        Смещение списка элементов
        """
        if self.count == 0:
            return 0
        return (self.page - 1) * self.per_page

    @property
    def has_next(self):
        """
        Возвращает True, если существует следующая страница
        """
        if self.count == 0:
            return False
        return True if self.page < self.pages else False

    @property
    def has_prev(self):
        """
        Возвращает True, если существует предыдущая страница
        """
        if self.count == 0:
            return False
        return True if self.page != 1 else False

    def __iter__(self):
        return iter(self.page_range)

    def url(self, page):
        """
        Возвращает адрес страницы
        """
        get = []
        for k, v in self.request.items():
            if not isinstance(v, (list, tuple)):
                v = [v]
            if k not in (self.page_arg, self.per_page_arg):
                for i in v:
                    get.append("%s=%s" % (k, i))
        get.append("%s=%s" % (self.page_arg, str(page)))
        get.append("%s=%s" % (self.per_page_arg, str(self.per_page)))
        return self.path + "?" + "&".join(get)
