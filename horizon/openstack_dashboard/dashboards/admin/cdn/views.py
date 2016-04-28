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
from horizon.utils import csvbase
from horizon import tables
from openstack_dashboard.dashboards.admin.cdn import tables\
    as cdn_tables
from openstack_dashboard.dashboards.cdn import middware
from openstack_dashboard.dashboards.cdn.cdn_domain_manager.models import Domain


# class GlobalUsage(middware.BaseUsage):
#     show_terminated = True
#
#     def get_usage_list(self, start, end):
#         data = middware.get_all_data(start, end)
#         return data
#
#
# class GlobalUsageCsvRenderer(csvbase.BaseCsvResponse):
#
#     columns = [_("Project Name"), _("User Name"), _("Domain Count"), _("Total Flow"), _("Total Requests"), _("Time Section")]
#
#     def get_row_data(self):
#
#         for u in self.context['usage'].usage_list:
#             yield (u.Project_name,
#                    u.User_name,
#                    u.Cdn_count,
#                    u.Total_Flow,
#                    u.Total_Requests,
#                    u.Time_Section)
#
#
# class GlobalOverview(middware.MyUsageView):
#     table_class = cdn_tables.GlobalUsageTable
#     usage_class = GlobalUsage
#     template_name = 'admin/cdn/usage.html'
#     csv_response_class = GlobalUsageCsvRenderer
#     page_title = _("Cdn Data Statistics")
#
#     def get_context_data(self, **kwargs):
#         context = super(GlobalOverview, self).get_context_data(**kwargs)
#         return context
#
#     def get_data(self):
#         try:
#             data = super(GlobalOverview, self).get_data()
#         except Exception:
#             data = []
#             exceptions.handle(self.request,
#                               _('Unable to retrieve data'))
#         return data


class AllDomainDetail(tables.DataTableView):
    table_class = cdn_tables.AllDomain
    template_name = 'admin/cdn/detail.html'
    page_title = _("Domain List")


    def get_data(self):
        try:
            domain_list = Domain.objects.all().order_by('project_name')
            query_filter = self.get_filters({})
            if query_filter:
                domain_list = Domain.objects.all().filter(**query_filter).order_by('project_name')
        except Exception:
            domain_list = []
            exceptions.handle(self.request,
                              _('Unable to retrieve domain list'))
        return domain_list

    def get_filters(self, filters):
        filter_field = self.table.get_filter_field()
        filter_action = self.table._meta._filter_action
        if filter_action.is_api_filter(filter_field):
            filter_string = self.table.get_filter_string()
            if filter_field and filter_string:
                filters[filter_field] = filter_string
        return filters


class TenantUsage(middware.BaseUsage):
    show_terminated = True

    def get_usage_list(self, start, end):
        if not self.domain_list:
            return []
        domain_id = self.request.GET.get('domain_id')
        domain_id = domain_id if domain_id else self.domain_list[0][0]
        data = middware.get_mon_data(str(start), str(end), domain_id)
        return data

#
# class TenantUsageCsvRenderer(csvbase.BaseCsvResponse):
#     columns = [_("Date"),_("IO"), _("Flow"), _("Requests")]
#
#     def get_row_data(self):
#
#         for u in self.context['usage'].usage_list:
#             yield (u.date,
#                    u.top_io,
#                    u.total_flow,
#                    u.total_requests,
#                    )


class TenantDetailView(middware.MyUsageView):
    table_class = cdn_tables.TenantUsageTable
    usage_class = TenantUsage
    template_name = 'admin/cdn/tenant.html'
    # csv_response_class = TenantUsageCsvRenderer
    page_title = _("Cdn Data Statistics")

    def get_domain(self):
        tenant_id = self.kwargs.get('tenant_id')
        domains = Domain.objects.filter(tenant_id=tenant_id).exclude(status='deleted').exclude(domain_id=None)
        self.usage_class.domain_list = [(i.domain_id, i.domain_name) for i in domains]
        return

    def get_context_data(self, **kwargs):
        context = super(TenantDetailView, self).get_context_data(**kwargs)
        domain_list = self.usage_class.domain_list
        context['usage'] = self.usage
        context['domain_from'] = self.usage.get_domain_id(domain_list)
        return context

    def get_data(self):
        try:
            self.get_domain()
            data = super(TenantDetailView, self).get_data()
        except Exception:
            data = []
            exceptions.handle(self.request,
                              _('Unable to retrieve domain list.'))

        return data


class DomainDetailView(TenantDetailView):

    def get_domain(self):
        domain_id = self.kwargs.get('domain_id')
        domains = Domain.objects.filter(domain_id=domain_id)
        self.usage_class.domain_list = [(i.domain_id, i.domain_name) for i in domains]
        return


