# -*- coding: utf-8 -*-
'''
Created on 2015-06-05

@author: yanjj@syscloud.cn
'''

from django.utils.translation import ugettext_lazy as _
from horizon import tabs
from openstack_dashboard.dashboards.project.cdn.cdn_cache_refresh \
    import tables
from openstack_dashboard.dashboards.project.cdn.cdn_cache_refresh import constants
from openstack_dashboard.dashboards.project.cdn import middware
from django.core.urlresolvers import reverse_lazy
from django.utils import timezone
import datetime


class URLRefreshTab(tabs.Tab):
    name = _("URL Fresh")
    template_name = 'cdn/cdn.cdn_cache_refresh/url_refresh.html'
    slug = "url_refresh"
    submit_url = reverse_lazy('horizon:cdn:cdn.cdn_cache_refresh:urlfresh')

    def get_context_data(self, request, **kwargs):
        return {'submit_url': self.submit_url}


class DirectoryRefreshTab(tabs.Tab):
    name = _("Directory Fresh")
    template_name = "cdn/cdn.cdn_cache_refresh/dir_refresh.html"
    slug = "directory_refresh"
    submit_url = reverse_lazy('horizon:cdn:cdn.cdn_cache_refresh:dirfresh')

    def get_context_data(self, request, **kwargs):
        return {'submit_url': self.submit_url}


class RefreshScheduleTab(tabs.TableTab):
    table_classes = (tables.UrlRef,)
    name = _("Fresh Schedule")
    slug = "refresh_schedule"
    template_name = constants.INFO_DETAIL_TEMPLATE_NAME

    @property
    def today(self):
        return timezone.now()

    @staticmethod
    def get_start(year, month, day):
        start = datetime.datetime(year, month, day, 0, 0, 0)
        return timezone.make_aware(start, timezone.utc)

    def get_cache_data(self):
        tenant_id = self.request.user.tenant_id
        args_start = (self.today.year, self.today.month, 1)
        start = self.get_start(*args_start)
        end = datetime.datetime.now()+datetime.timedelta(hours=8)
        data = middware.get_purge_data(dateFrom=start.strftime("%Y-%m-%d %H:%M:%S"),
                                       dateTo=end.strftime("%Y-%m-%d %H:%M:%S"), tenant_id=tenant_id)
        return data

    def get_context_data(self, request, **kwargs):
        context = super(RefreshScheduleTab, self).get_context_data(request, **kwargs)
        context["cache_table"] = self.get_cache_data()
        return context


class CacheRefreshTabs(tabs.TabGroup):
    slug = "cache_refresh"
    tabs = (URLRefreshTab, DirectoryRefreshTab, RefreshScheduleTab)
    sticky = True