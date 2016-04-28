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

from django import conf
from django.utils.translation import ugettext_lazy as _

from horizon import tabs
from openstack_dashboard import api

class OverviewTab(tabs.Tab):
    name = _("Overview")
    slug = "overview"
    template_name = "project/virtnic/_detail_overview.html"

    def get_context_data(self, request):
        port = self.tab_group.kwargs['port']
        if port.fixed_ips:
            port.inner_ip= port.fixed_ips[0]["ip_address"]
        search_opts={"tenant_id":self.request.user.tenant_id,"fixed_port_id":port.id}
        floating_ip=api.network.floating_ip_list_by_ip(request,**search_opts)
        if floating_ip:
            port.floating_ip=floating_ip[0]["floating_ip_address"]
        else:
            port.floating_ip=None
        network=api.neutron.network_get(request, port.network_id)
        port.subnet=network.name
        if port.device_id:
            nova=api.nova.server_get(request, port.device_id)
            port.host=nova.name
        else:
            port.host=None
        return {"port":port}

class VirtnicDetailTabs(tabs.TabGroup):
    slug = "i_details"
    tabs = (OverviewTab,)
