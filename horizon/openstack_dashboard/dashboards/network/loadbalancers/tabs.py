#    Copyright 2013, Big Switch Networks, Inc.
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

from openstack_dashboard import api

from openstack_dashboard.dashboards.network.loadbalancers import tables


class PoolsTab(tabs.TableTab):
    table_classes = (tables.PoolsTable,)
    name = _("Pools")
    slug = "pools"
    template_name = "horizon/common/_detail_table.html"

    def get_poolstable_data(self):
        try:
            tenant_id = self.request.user.tenant_id
            pools = api.lbaas.pool_list(self.tab_group.request,
                                        tenant_id=tenant_id)
        except Exception:
            pools = []
            exceptions.handle(self.tab_group.request,
                              _('Unable to retrieve pools list.'))
        return pools


class MembersTab(tabs.TableTab):
    table_classes = (tables.MembersTable,)
    name = _("Members")
    slug = "members"
    template_name = "horizon/common/_detail_table.html"

    def get_memberstable_data(self):
        try:
            tenant_id = self.request.user.tenant_id
            members = api.lbaas.member_list(self.tab_group.request,
                                            tenant_id=tenant_id)
        except Exception:
            members = []
            exceptions.handle(self.tab_group.request,
                              _('Unable to retrieve member list.'))
        return members


class MonitorsTab(tabs.TableTab):
    table_classes = (tables.MonitorsTable,)
    name = _("Monitors")
    slug = "monitors"
    template_name = "horizon/common/_detail_table.html"

    def get_monitorstable_data(self):
        try:
            tenant_id = self.request.user.tenant_id
            monitors = api.lbaas.pool_health_monitor_list(
                self.tab_group.request, tenant_id=tenant_id)
        except Exception:
            monitors = []
            exceptions.handle(self.tab_group.request,
                              _('Unable to retrieve monitor list.'))
        return monitors


class LoadBalancerTab(tabs.TableTab):
    table_classes = (tables.LoadBalancersTable,)
    name = _("LoadBalancer")
    slug = "loadbalancers"
    template_name = "horizon/common/_detail_table.html"

    def get_loadbalancerstable_data(self):
        modified_pools = []
        try:
            tenant_id = self.request.user.tenant_id
            pools = api.lbaas.pool_list(self.tab_group.request,
                            tenant_id=tenant_id)
            # add name to match
            for p in pools:
                if  p.vip_id:
                    vip = api.lbaas.vip_get(self.tab_group.request, p.vip_id)
                    p.internal_ip = vip.address
                    fips = api.network.tenant_floating_ip_list(self.tab_group.request)
                    vip_fip = [fip for fip in fips
                               if fip.port_id == vip.port_id]
                    if vip_fip:
                        p.floating_ip = vip_fip[0].floating_ip_address
                modified_pools.append(p)
        except Exception:
            pools = []
            exceptions.handle(self.tab_group.request,
                              _('Unable to retrieve loadbalancer list.'))
        return modified_pools


class LoadBalancerTabs(tabs.TabGroup):
    slug = "lbtabs"
#     tabs = (PoolsTab, MembersTab, MonitorsTab, LoadBalancerTab)
    tabs = (LoadBalancerTab,)
    sticky = True


class PoolDetailsTab(tabs.Tab):
    name = _("Pool Details")
    slug = "pooldetails"
    template_name = "network/loadbalancers/_pool_details.html"

    def get_context_data(self, request):
        pool = self.tab_group.kwargs['pool']
        return {'pool': pool}


class VipDetailsTab(tabs.Tab):
    name = _("VIP Details")
    slug = "vipdetails"
    template_name = "network/loadbalancers/_vip_details.html"

    def get_context_data(self, request):
        vid = self.tab_group.kwargs['vip_id']
        try:
            vip = api.lbaas.vip_get(request, vid)
        except Exception:
            vip = []
            exceptions.handle(self.tab_group.request,
                              _('Unable to retrieve VIP details.'))
        return {'vip': vip}


class MemberDetailsTab(tabs.Tab):
    name = _("Member Details")
    slug = "memberdetails"
    template_name = "network/loadbalancers/_member_details.html"

    def get_context_data(self, request):
        member = self.tab_group.kwargs['member']
        return {'member': member}


class MonitorDetailsTab(tabs.Tab):
    name = _("Monitor Details")
    slug = "monitordetails"
    template_name = "network/loadbalancers/_monitor_details.html"

    def get_context_data(self, request):
        monitor = self.tab_group.kwargs['monitor']
        return {'monitor': monitor}


class LoadBalancerDetailsTab(tabs.Tab):
    name = _("LoadBalancer Details")
    slug = "loadbalancerdetails"
    template_name = "network/loadbalancers/_loadbalancer_details.html"

    def get_context_data(self, request):
        pool = self.tab_group.kwargs['pool']
        return {'pool': pool}


class PoolDetailsTabs(tabs.TabGroup):
    slug = "pooltabs"
    tabs = (PoolDetailsTab,)


class VipDetailsTabs(tabs.TabGroup):
    slug = "viptabs"
    tabs = (VipDetailsTab,)


class MemberDetailsTabs(tabs.TabGroup):
    slug = "membertabs"
    tabs = (MemberDetailsTab,)


class MonitorDetailsTabs(tabs.TabGroup):
    slug = "monitortabs"
    tabs = (MonitorDetailsTab,)


class LoadBalancerDetailsTabs(tabs.TabGroup):
    slug = "loadbalancertabs"
    tabs = (LoadBalancerDetailsTab,)
