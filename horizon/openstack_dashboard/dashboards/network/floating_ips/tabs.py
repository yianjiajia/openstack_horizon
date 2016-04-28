# Copyright 2012 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
#
# Copyright 2012 Nebula, Inc.
# Copyright 2012 OpenStack Foundation
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
from horizon import tabs

from neutronclient.common import exceptions as neutron_exc

from openstack_dashboard.api import keystone
from openstack_dashboard.api import network
from openstack_dashboard.api import nova

from openstack_dashboard.dashboards.network.\
        floating_ips.tables import FloatingIPsTable


class FloatingIPsTab(tabs.TableTab):
    table_classes = (FloatingIPsTable,)
    name = _("Floating IPs")
    slug = "floating_ips_tab"
    template_name = "horizon/common/_detail_table.html"
    permissions = ('openstack.services.compute',)

    def get_floating_ips_data(self):
        try:
            floating_ips = network.tenant_floating_ip_list(self.request)
        except neutron_exc.ConnectionFailed:
            floating_ips = []
            exceptions.handle(self.request)
        except Exception:
            floating_ips = []
            exceptions.handle(self.request,
                              _('Unable to retrieve floating IP addresses.'))

        try:
            floating_ip_pools = network.floating_ip_pools_list(self.request)
        except neutron_exc.ConnectionFailed:
            floating_ip_pools = []
            exceptions.handle(self.request)
        except Exception:
            floating_ip_pools = []
            exceptions.handle(self.request,
                              _('Unable to retrieve floating IP pools.'))
        pool_dict = dict([(obj.id, obj.name) for obj in floating_ip_pools])

        instances = []
        try:
            instances, has_more = nova.server_list(self.request)
        except Exception:
            exceptions.handle(self.request,
                              _('Unable to retrieve instance list.'))

        instances_dict = dict([(obj.id, obj.name) for obj in instances])

        for ip in floating_ips:
            ip.instance_name = instances_dict.get(ip.instance_id)
            ip.pool_name = pool_dict.get(ip.pool, ip.pool)

        return floating_ips

    def allowed(self, request):
        return network.floating_ip_supported(request)


class FloatingIpsTabs(tabs.TabGroup):
    slug = "floating_ips_tabs"
    tabs = (FloatingIPsTab,)
    sticky = True
