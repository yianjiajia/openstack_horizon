# Copyright 2012,  Nachi Ueno,  NTT MCL,  Inc.
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

"""
Views for managing Neutron Routers.
"""

from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext_lazy as _
from django.conf import settings

from horizon import exceptions
from horizon.utils import functions as utils

from openstack_dashboard import api
from openstack_dashboard.dashboards.admin.networks import views as n_views
from openstack_dashboard.dashboards.admin.routers import forms as rforms
from openstack_dashboard.dashboards.admin.routers import tables as rtbl
from openstack_dashboard.dashboards.admin.routers import tabs as rtabs
from openstack_dashboard.dashboards.network.routers import views as r_views


class IndexView(r_views.IndexView, n_views.IndexView):
    table_class = rtbl.RoutersTable
    template_name = 'admin/routers/index.html'

    def has_prev_data(self, table):
        return self._prev

    def has_more_data(self, table):
        return self._more

    def _get_routers(self, search_opts=None):
        self._prev = self._more = False
        prev_marker = self.request.GET.get(
            rtbl.RoutersTable._meta.prev_pagination_param)
        if prev_marker is not None:
            page_reverse = True
            marker = prev_marker
        else:
            page_reverse = False
            marker = self.request.GET.get(
                rtbl.RoutersTable._meta.pagination_param)
        search_opts = self.get_filters({})
        search_opts['retrieve_all'] = False
        search_opts['page_reverse'] = page_reverse
        page_size = utils.get_page_size(self.request) or getattr(settings, 'API_RESULT_LIMIT', 1000)
        search_opts['limit'] = page_size + 1
        search_opts['marker'] = marker or ''
        try:
            routers = api.neutron.router_list_admin(self.request,
                                              **search_opts)
        except Exception:
            routers = []
            exceptions.handle(self.request,
                              _('Unable to retrieve router list.'))
        if routers:
            tenant_dict = self._get_tenant_list()
            ext_net_dict = self._list_external_networks()

            self._prev = False
            self._more = False
            if len(routers) > page_size:
                if page_reverse:
                    routers = routers[1:len(routers)]
                else:
                    routers.pop()
                self._more = True
                if marker is not None:
                    self._prev = True
            elif page_reverse and marker is not None:
                self._more = True
            elif marker is not None:
                self._prev = True

            for r in routers:
                # Set tenant name
                tenant = tenant_dict.get(r.tenant_id, None)
                r.tenant_name = getattr(tenant, 'name', None)
                # If name is empty use UUID as name
                r.name = r.name_or_id
                # Set external network name
                self._set_external_network(r, ext_net_dict)

        return routers

    def get_filters(self, filters):
        filter_field = self.table.get_filter_field()
        filter_action = self.table._meta._filter_action
        if filter_action.is_api_filter(filter_field):
            filter_string = self.table.get_filter_string()
            if filter_field and filter_string:
                filters[filter_field] = filter_string
        return filters

    def get_data(self):
        routers = self._get_routers()
        return routers


class DetailView(r_views.DetailView):
    tab_group_class = rtabs.RouterDetailTabs
    template_name = 'admin/routers/detail.html'
    failure_url = reverse_lazy('horizon:admin:routers:index')

    def get_context_data(self, **kwargs):
        context = super(DetailView, self).get_context_data(**kwargs)
        table = rtbl.RoutersTable(self.request)
        context["url"] = self.failure_url
        context["actions"] = table.render_row_actions(context["router"])
        return context


class UpdateView(r_views.UpdateView):
    form_class = rforms.UpdateForm
    template_name = 'network/routers/update.html'
    success_url = reverse_lazy("horizon:admin:routers:index")
    submit_url = "horizon:admin:routers:update"
