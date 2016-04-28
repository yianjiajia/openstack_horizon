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

import json
import datetime

from django.template.defaultfilters import capfirst  # noqa
from django.template.defaultfilters import floatformat  # noqa
from django.utils.translation import ugettext_lazy as _

from horizon.utils import csvbase
from horizon import views

from openstack_dashboard import usage
from openstack_dashboard import api
from openstack_dashboard.api import billing
from openstack_dashboard.api.member.member import UserCenter


class ProjectUsageCsvRenderer(csvbase.BaseCsvResponse):
    columns = [_("Instance Name"), _("VCPUs"), _("RAM (MB)"),
               _("Disk (GB)"), _("Usage (Hours)"),
               _("Time since created (Seconds)"), _("State")]

    def get_row_data(self):
        for inst in self.context['usage'].get_instances():
            yield (inst['name'],
                   inst['vcpus'],
                   inst['memory_mb'],
                   inst['local_gb'],
                   floatformat(inst['hours'], 2),
                   inst['uptime'],
                   capfirst(inst['state']))


class ProjectOverview(usage.UsageView):
    table_class = usage.ProjectUsageTable
    usage_class = usage.ProjectUsage
    template_name = 'overview/overview/usage.html'
    csv_response_class = ProjectUsageCsvRenderer

    def get_data(self):
        super(ProjectOverview, self).get_data()
        return self.usage.get_instances()

    def get_context_data(self, **kwargs):
        context = super(ProjectOverview, self).get_context_data(**kwargs)

        tenant_id = self.request.user.tenant_id
        firewalls = api.fwaas.firewall_list_for_tenant(self.request, tenant_id)
        rules = api.fwaas.rule_list_for_tenant(self.request, tenant_id)
        policies = api.fwaas.policy_list_for_tenant(self.request, tenant_id)
        if len(firewalls) > 0 or len(rules) > 0 or len(policies) > 0:
            context['firewall_init'] = 1
        else:
            context['firewall_init'] = 0

        sslvpncredentials = api.vpn.sslvpncredential_list(self.request, tenant_id=tenant_id)
        vpnservices = api.vpn.vpnservice_list(self.request, tenant_id=tenant_id)
        sslvpnconnections = api.vpn.sslvpnconnection_list(self.request, tenant_id=tenant_id)
        if len(sslvpncredentials) > 0 or len(vpnservices) > 0 or len(sslvpnconnections) > 0:
            context['vpn_init'] = 1
        else:
            context['vpn_init'] = 0

        # keypair
        keypairs = api.nova.keypair_list(self.request)
        if len(keypairs) > 0:
            context['keypair_init'] = 1
        else:
            context['keypair_init'] = 0

        # fee info
        account = billing.RequestClient(self.request).get_account()
        if account:
            context['balance'] = float(account['cash_balance']) + float(account['gift_balance'])
        else:
            context['balance'] = 0.0
        if account['status'] == 'frozen':
            context['account_is_frozen'] = 1
        else:
            context['account_is_frozen'] = 0
        context['vpn_count'] = len(sslvpnconnections)
        bill_client = billing.BillingItem(self.request)
        bill_items = bill_client.billing_item()

        servers, unused = api.nova.server_list(self.request)
        volumes = api.cinder.volume_list(self.request)
        snapshots = api.cinder.volume_snapshot_list(self.request)
        # fees
        instance_fee = 0.0
        for server in servers:
            if server.status == 'ACTIVE':
                instance_fee = instance_fee + bill_items['cpu_1_core'] * server.vcpus + \
                               bill_items['memory_1024_M'] * server.memory_mb/1024.0 +\
                               bill_items['instance_1']
            elif server.status == 'SHUTOFF':
                instance_fee = instance_fee + bill_items['instance_1']
                
        volume_fee = 0.0
        volume_size = 0
        for volume in volumes:
            if volume.status in ['in-use', 'available']:
                volume_fee = volume_fee + bill_items['disk_1_G'] * volume.size
                volume_size = volume_size + volume.size

        snapshot_fee = 0.0
        snapshot_size = 0
        for snapshot in snapshots:
            if snapshot.status in ['in-use', 'available']:
                snapshot_fee = snapshot_fee + bill_items['snapshot_1_G'] * snapshot.size
                snapshot_size = snapshot_size + snapshot.size
        routers = api.neutron.router_list(self.request, tenant_id=tenant_id)
        router_fee = 0.0
        bandwidth_fee = 0.0
        bandwidth_count = 0
        for router in routers:
            if router.tenant_id == self.request.user.tenant_id:
                router_fee = router_fee + bill_items['router_1']
                bandwidth_fee = bandwidth_fee + bill_items['bandwidth_1_M'] * router.bandwidth
                bandwidth_count = bandwidth_count + router.bandwidth

        # if have router, disable net_init button
        if len(routers) > 0:
            context['have_routers'] = 1
        else:
            context['have_routers'] = 0

        context['instance_fee'] = round(instance_fee * 24, 4)
        context['volume_fee'] = round(volume_fee * 24, 4)
        context['snapshot_fee'] = round(snapshot_fee * 24, 4)
        context['volume_size'] = volume_size
        context['snapshot_size'] = snapshot_size

        context['router_fee'] = round(router_fee * 24, 4)
        context['bandwidth_fee'] = round(bandwidth_fee * 24, 4)
        context['bandwidth_count'] = bandwidth_count
        context['fip_fee'] = round(bill_items['ip_1'] * context['usage'].limits['totalFloatingIpsUsed'] * 24, 4)
        context['vpn_fee'] = round(bill_items['vpn_1'] * len(sslvpnconnections) * 24, 4)

        cdn_fee_width = 0.0
        cdn_fee_flow = 0.0
        if account:
            bill_client = billing.RequestClient(self.request)
            now = datetime.datetime.utcnow()
            today = datetime.datetime(now.year, now.month, now.day)
            delta = datetime.timedelta(days=-1)
            last_day = (today + delta).strftime("%Y-%m-%d")
            today = today.strftime("%Y-%m-%d")

            ret_one_day = json.loads(bill_client.api_request('/consumption/getconsumptionsummary/' + account['account_id'] +
                                    '?started_at=' +last_day + '&ended_at=' + today).read())

            if ret_one_day['success'] == 'success':
                consumption = ret_one_day['consumptionsummary']
                cdn_fee_item_bandwidth = [c for c in consumption if c['resource_type'] == 'cdnbandwidth']
                if cdn_fee_item_bandwidth:
                    cdn_fee_width = float(cdn_fee_item_bandwidth[0]['amount_total'])

                cdn_fee_item_flow = [c for c in consumption if c['resource_type'] == 'cdnflow']
                if cdn_fee_item_flow:
                    cdn_fee_flow = float(cdn_fee_item_flow[0]['amount_total'])
        context['cdn_fee'] = round(cdn_fee_width + cdn_fee_flow, 4)

        context['est_comsume_one_day'] = context['instance_fee'] + context['volume_fee'] + context['snapshot_fee'] +\
                                         context['fip_fee'] + context['router_fee'] + context['vpn_fee'] + \
                                         context['cdn_fee'] + context['bandwidth_fee']
        
        userCenter=UserCenter()
        user=userCenter.getById(self.request.user.id)
        context['login_last']=user.login_last
        userCenter.updateUser(self.request.user.id,{'login_last':datetime.datetime.utcnow()})
        context['balance_ceditline'] = float(account['cash_balance']) + float(account['gift_balance'])  + float(account['credit_line']) 
        return context


class WarningView(views.HorizonTemplateView):
    template_name = "project/_warning.html"


from horizon import forms
from openstack_dashboard.dashboards.overview.overview import forms as init_form
from django.core.urlresolvers import reverse_lazy


class InitNetView(forms.ModalFormView):
    form_id = "network_init_modal"
    modal_header = _("Network Init")
    page_title = _("Network Init")
    form_class = init_form.InitNetForm
    template_name = 'overview/overview/initNetwork.html'
    submit_url = reverse_lazy("horizon:overview:overview:initnet")
    success_url = reverse_lazy("horizon:overview:overview:index")
    submit_label = _("Confirm")


class InitVPNView(forms.ModalFormView):
    form_id = "vpn_init_modal"
    modal_header = _("VPN Init")
    page_title = _("VPN Init")
    form_class = init_form.InitVPNForm
    template_name = 'overview/overview/initVPN.html'
    submit_url = reverse_lazy("horizon:overview:overview:initvpn")
    success_url = reverse_lazy("horizon:overview:overview:index")
    submit_label = _("Confirm")


class InitFirewallView(forms.ModalFormView):
    form_id = "firewall_init_modal"
    modal_header = _("Firewall Init")
    page_title = _("Firewall Init")
    form_class = init_form.InitFireWallForm
    template_name = 'overview/overview/initFirewall.html'
    submit_url = reverse_lazy("horizon:overview:overview:initfirewall")
    success_url = reverse_lazy("horizon:overview:overview:index")
    submit_label = _("Confirm")


class DestroyView(forms.ModalFormView):
    form_id = "destroy_modal"
    modal_header = _("Destroy all Resource")
    page_title = _("Destroy all Resource")
    submit_label = _("Confirm")
    form_class = init_form.DestroyForm

    template_name = 'overview/overview/destroy.html'
    submit_url = reverse_lazy("horizon:overview:overview:destroy")
    success_url = reverse_lazy("horizon:overview:overview:index")
