__author__ = 'yanjiajia'
# -*- coding: utf-8 -*-
'''
Created on 2015-06-05

@author: yanjj@syscloud.cn
'''

from django.utils.translation import ugettext_lazy as _
from horizon import tabs
from openstack_dashboard.dashboards.project.cdn.cdn_monitor_report \
    import tables
from openstack_dashboard.dashboards.project.cdn.cdn_monitor_report import constants
from openstack_dashboard import usage
from openstack_dashboard.dashboards.project.cdn.cdn_domain_manager.models import Domain
from openstack_dashboard.dashboards.project.cdn import middware


class MonitorChartTab(tabs.Tab, middware.BaseUsage):
    name = _("Monitor Chart")
    template_name = "cdn/cdn.cdn_monitor_report/chart.html"
    slug = "monitor_chart"

    def get_domain(self):
        tenant_id = self.request.user.tenant_id
        return Domain.objects.filter(tenant_id=tenant_id).exclude(status='deleted').exclude(domain_id=None)

    def get_context_data(self, request, **kwargs):
        return {'form': self.get_form(), 'domain': self.get_domain()}


class DataStatisticsTab(tabs.TableTab, middware.BaseUsage):
    table_classes = (tables.UsageTable,)
    name = _("Data Statistics")
    slug = "data_statistics"
    template_name = constants.INFO_DETAIL_TEMPLATE_NAME

    def get_context_data(self, request, **kwargs):
        context = super(DataStatisticsTab, self).get_context_data(request, **kwargs)
        self.load_table_data()
        for table_name, table in self._tables.items():
            if len(self.table_classes) == 1:
                context["table"] = table
            context["%s_table" % table_name] = table
        return context

    def get_usage_data(self):
        start, end = self.get_date_range()
        tenant_id = self.request.user.tenant_id
        data = middware.get_mon_data(start.strftime("%Y-%m-%d %H:%M:%S"),
                                     end.strftime("%Y-%m-%d %H:%M:%S"), tenant_id)
        return data


class MonitorReportTabs(tabs.TabGroup):
    slug = "monitor_report"
    tabs = (MonitorChartTab, DataStatisticsTab)
    sticky = True