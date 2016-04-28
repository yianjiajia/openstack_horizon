# Copyright 2012 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
#
# Copyright 2012 Nebula, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
from django.utils.translation import ugettext_lazy as _
from horizon import exceptions
from openstack_dashboard.dashboards.project.cdn.cdn_log_manager import tables \
    as log_table
from openstack_dashboard.dashboards.project.cdn.cdn_domain_manager.models\
    import Domain
from openstack_dashboard.dashboards.project.cdn import middware


class LogUsage(middware.BaseUsage):
    show_terminated = True

    def get_usage_list(self, start, end):
        try:
            data = []
            tenant_id = self.request.user.tenant_id
            report_form = middware.reportApi.ReportForm(dateFrom=str(start), dateTo=str(end), reportType='daily')
            domain_quset = [i for i in Domain.objects.filter(tenant_id=tenant_id) if i.domain_id is not None and i.status != 'deleted']
            log = middware.ReportManage()
            for i in domain_quset:
                ret = log.getLog(report_form, i.domain_id)
                if ret.getLogs() is None:
                    return []
                else:
                    for j in ret.getLogs():
                        log_class = middware.LogData(domain=i.domain_name, log_url=j.url,
                                                     size=j.fileSize, begin=j.dateFrom, end=j.dateTo)
                        data.append(log_class)
            return data
        except Exception:
            exceptions.handle(self.request,
                              _('Unable to retrieve data'))
            return []


class LogOverview(middware.MyUsageView):
    table_class = log_table.LogTable
    usage_class = LogUsage
    template_name = 'cdn/cdn.cdn_log_manager/usage.html'
    page_title = _("Cdn Log Manager")

    def get_context_data(self, **kwargs):
        context = super(LogOverview, self).get_context_data(**kwargs)
        return context

    def get_data(self):
        try:
            data = super(LogOverview, self).get_data()
        except Exception:
            data = []
            exceptions.handle(self.request,
                              _('Unable to retrieve data'))

        return data
