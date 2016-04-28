# Copyright 2012 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
#
# Copyright 2012 Nebula, Inc.
# Copyright (c) 2012 X.commerce, a business unit of eBay Inc.
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
Views for managing floating IPs.
"""

from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext_lazy as _

from neutronclient.common import exceptions as neutron_exc

from horizon import exceptions
from horizon import forms
from horizon import workflows
from horizon import tabs

from openstack_dashboard import api
from openstack_dashboard.usage import quotas

from openstack_dashboard.dashboards.network.\
    floating_ips import forms as project_forms
from openstack_dashboard.dashboards.network.\
    floating_ips import workflows as project_workflows
from openstack_dashboard.dashboards.network.floating_ips \
    import tabs as project_tabs

class IndexView(tabs.TabbedTableView):
    tab_group_class = project_tabs.FloatingIpsTabs
    template_name = 'network/floating_ips/index.html'
    page_title = _("Floating IPs")


class AssociateView(workflows.WorkflowView):
    workflow_class = project_workflows.IPAssociationWorkflow


class AllocateView(forms.ModalFormView):
    form_class = project_forms.FloatingIpAllocate
    form_id = "associate_floating_ip_form"
    modal_header = _("Allocate Floating IP")
    template_name = 'network/floating_ips/allocate.html'
    submit_label = _("Allocate IP")
    submit_url = reverse_lazy("horizon:network:floating_ips:allocate")
    success_url = reverse_lazy('horizon:network:floating_ips:index')

    def get_object_display(self, obj):
        return obj.ip

    # def get_context_data(self, **kwargs):
    #     context = super(AllocateView, self).get_context_data(**kwargs)
    #     try:
    #         context['usages'] = quotas.tenant_quota_usages(self.request)
    #     except Exception:
    #         exceptions.handle(self.request)
    #     return context

    def get_initial(self):
        try:
            pools = api.network.floating_ip_pools_list(self.request)
        except neutron_exc.ConnectionFailed:
            pools = []
            exceptions.handle(self.request)
        except Exception:
            pools = []
            exceptions.handle(self.request,
                              _("Unable to retrieve floating IP pools."))
        pool_list = [(pool.id, pool.name) for pool in pools]
        if not pool_list:
            pool_list = [(None, _("No floating IP pools available"))]
        return {'pool_list': pool_list}


class UpdateView(forms.ModalFormView):
    form_class = project_forms.FloatingIpUpdate
    form_id = "update_floating_ip_form"
    modal_header = _("Update Floating IP")
    template_name = 'network/floating_ips/update.html'
    submit_label = _("Update IP")
    submit_url = reverse_lazy("horizon:network:floating_ips:update")
    success_url = reverse_lazy('horizon:network:floating_ips:index')
    
    def get_object(self):
        try:
            floating_ip_id = self.request.GET.get('floating_ip_id')
            
            if floating_ip_id is None:
                floating_ip_id = self.request.POST.get('floating_ip_id')

            return api.network.tenant_floating_ip_get(self.request, floating_ip_id)
        except Exception:
            msg = _('Unable to update floating IP.')
            url = reverse_lazy('horizon:network:floating_ips:index')
            exceptions.handle(self.request, msg, redirect=url)

    def get_context_data(self, **kwargs):
        context = super(UpdateView, self).get_context_data(**kwargs)
        return context

    def get_initial(self):
        fip = self.get_object()
        return {'floating_ip_id': fip.id,
                'floating_ip_address': fip.floating_ip_address,
                'limit_speed': fip.limit_speed,
                'is_fixed_ip_address': (True if fip.fixed_ip_address else False),
                'fixed_ip_address': fip.fixed_ip_address,
                'port_id': fip.port_id}


