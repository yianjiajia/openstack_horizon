# -*- coding:utf-8 -*-

class PageResult(list):
    
    def __init__(self, total=0, page_no=1, page_size=15, edge_size=0):
        """
        total:总记录数
        page_no:当前页数
        page_size：每页记录条数
        edge_size:滑窗的大小
        """
        self.total = total
        self.page_size = page_size if page_size > 0 else 0
        self.edge_size = edge_size if edge_size > 0 else 0

        if page_no <= 0:
            self.no = 1
        elif self.max >= 1 and page_no > self.max:
            self.no = self.max
        else:
            self.no = page_no

    @property
    def start(self):
        return (self.no - 1) * self.page_size

    @property
    def max(self):
        """总页数"""
        if self.page_size > 0:
            return (self.total + self.page_size - 1) / self.page_size
        else:  # 不分页，显示全部条目
            return 1

    @property
    def has_prev(self):
        """是否有上一页"""
        return self.no > 1

    @property
    def has_next(self):
        """是否有下一页"""
        return self.no < self.max

    @property
    def slider(self):
        """显示滑窗大小"""
        if self.edge_size > 0:
            start = max(self.no - self.edge_size, 1)
            stop = min(self.no + self.edge_size, self.max)
        else: 
            start, stop = 1, self.max
        return range(start, stop + 1)

    def clear(self):
        del self[:]

    def get_pagination(self):
        return Pagintion(self.no, self.max, self.has_prev, self.has_next, self.slider)


class Pagintion(object):
    '''分页对象'''
    def __init__(self, page_no, page_count, has_prev, has_next, page_range):
        """
        :rtype : object
        """
        self.page_no = page_no
        self.page_count = page_count
        self.has_prev = has_prev
        self.has_next = has_next
        self.page_range = page_range