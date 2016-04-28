__author__ = 'yanjiajia'

from django.utils.translation import ugettext_lazy as _
from horizon import tables




class LogFilter(tables.FilterAction):
    def filter(self, table, logs, filter_string):
        """log filter"""
        query = filter_string.lower()
        return [log for log in logs
                if query in log.name.lower()]


class LogTable(tables.DataTable):
    domain_name = tables.Column('domain_name', verbose_name=_("Domain Name"))
    log_url = tables.Column('log_url', verbose_name=_("Download Url"))
    log_size = tables.Column('log_size', verbose_name=_("Log Size(byte)"))
    begin = tables.Column('begin', verbose_name=_("Begin"))
    end = tables.Column('end', verbose_name=_("End"))

    def get_object_id(self, datum):
        return datum.log_url

    class Meta(object):
        name = "log"
        hidden_title = True
        verbose_name = _("Log")
        columns = ("domain_name", "log_url", "log_size", "begin",
                   "end")
        table_actions = (LogFilter,)
        multi_select = False





