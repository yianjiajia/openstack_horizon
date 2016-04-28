__author__ = 'yanjiajia'
# -*- coding: utf-8 -*-
'''
Created on 2015-06-05

@author: yanjj@syscloud.cn
'''

from django.utils.translation import ugettext_lazy as _
from horizon import tabs
from openstack_dashboard.dashboards.cdn.cdn_monitor_report \
    import tables
from openstack_dashboard.dashboards.cdn.cdn_monitor_report import constants
from openstack_dashboard.dashboards.cdn.cdn_domain_manager.models import Domain
from openstack_dashboard.dashboards.cdn import middware


class MonitorChartTab(tabs.Tab, middware.BaseUsage):
    name = _("Monitor Chart")
    template_name = "cdn/cdn_monitor_report/chart.html"
    slug = "monitor_chart"
    preload = False

    def get_domain(self):
        tenant_id = self.request.user.tenant_id
        domain_list = Domain.objects.filter(tenant_id=tenant_id).exclude(status='deleted').exclude(domain_id=None)
        return domain_list


    def get_context_data(self, request, **kwargs):
        return {'form': self.get_form(), 'domain': self.get_domain()}


class DataStatisticsTab(tabs.TableTab, middware.BaseUsage):
    table_classes = (tables.UsageTable,)
    name = _("Data Statistics")
    slug = "data_statistics"
    template_name = constants.INFO_DETAIL_TEMPLATE_NAME
    preload = False

    def get_domain(self):
        tenant_id = self.request.user.tenant_id
        domains = Domain.objects.filter(tenant_id=tenant_id).exclude(status='deleted').exclude(domain_id=None)
        return [(i.domain_id, i.domain_name) for i in domains]

    def get_context_data(self, request, **kwargs):
        context = super(DataStatisticsTab, self).get_context_data(request, **kwargs)
        self.load_table_data()
        for table_name, table in self._tables.items():
            if len(self.table_classes) == 1:
                context["table"] = table
            context["%s_table" % table_name] = table
        context['form'] = self.get_form()
        domain_list = self.domain_list
        context['domain_from'] = self.get_domain_id(domain_list)
        return context

    def get_usage_data(self):
        self.domain_list = self.get_domain()
        start = self.request.GET.get('start')
        end = self.request.GET.get('end')
        if not self.domain_list:
            return []
        if start == '' or end == '':
            return []
        start = start if start else self.get_form().data.get('start')
        end = end if end else self.get_form().data.get('end')
        domain_id = self.request.GET.get('domain_id')
        domain_id = domain_id if domain_id else self.domain_list[0][0]
        data = middware.get_mon_data(' '.join([start, '00:00:00']), ' '.join([end, '23:59:59']), domain_id)
        return data


class MonitorReportTabs(tabs.TabGroup):
    slug = "monitor_report"
    tabs = (MonitorChartTab, DataStatisticsTab)
    sticky = True