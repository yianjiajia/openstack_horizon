__author__ = 'yanjiajia'
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext_lazy
from horizon import tables


class MyFilterAction(tables.FilterAction):

    def filter(self, table, domains, filter_string):
        """result filter"""
        query = filter_string.lower()
        return [router for router in domains
                if query in router.name.lower()]


class ReFresh(tables.LinkAction):
    name = "refresh"
    verbose_name = _("Refresh")
    url = "horizon:cdn:cdn_cache_refresh:index"
    icon = "refresh"


class UrlRef(tables.DataTable):
    cache_type = tables.Column("cache_type", verbose_name=_("Cache Type"))
    cache_time = tables.Column("cache_time", verbose_name=_("Cache Time"))
    status = tables.Column('status', verbose_name=_("Status"))

    def get_object_id(self, datum):
        return datum.cache_type

    class Meta(object):
        name = "cache"
        verbose_name = _("Cache Fresh")
        table_actions = (ReFresh, MyFilterAction)



