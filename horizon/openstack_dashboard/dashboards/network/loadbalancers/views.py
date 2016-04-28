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

from django.core.urlresolvers import reverse
from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import forms
from horizon import messages
from horizon import tabs
from horizon.utils import memoized
from horizon import workflows

from openstack_dashboard import api
from openstack_dashboard.dashboards.network.loadbalancers \
    import forms as project_forms
from openstack_dashboard.dashboards.network.loadbalancers \
    import tables as project_tables
from openstack_dashboard.dashboards.network.loadbalancers \
    import tabs as project_tabs
from openstack_dashboard.dashboards.network.loadbalancers import utils
from openstack_dashboard.dashboards.network.loadbalancers \
    import workflows as project_workflows

import re


class IndexView(tabs.TabbedTableView):
    tab_group_class = (project_tabs.LoadBalancerTabs)
    template_name = 'network/loadbalancers/details_tabs.html'
    page_title = _("Load Balancer")

    def post(self, request, *args, **kwargs):
        obj_ids = request.POST.getlist('object_ids')
        action = request.POST['action']
        m = re.search('.delete([a-z]+)', action).group(1)
        if obj_ids == []:
            obj_ids.append(re.search('([0-9a-z-]+)$', action).group(1))
        if m == 'monitor':
            for obj_id in obj_ids:
                try:
                    api.lbaas.pool_health_monitor_delete(request, obj_id)
                    messages.success(request, _('Deleted monitor %s') % obj_id)
                except Exception as e:
                    exceptions.handle(request,
                                      _('Unable to delete monitor. %s') % e)
        if m == 'pool':
            for obj_id in obj_ids:
                try:
                    api.lbaas.pool_delete(request, obj_id)
                    messages.success(request, _('Deleted pool %s') % obj_id)
                except Exception as e:
                    exceptions.handle(request,
                                      _('Unable to delete pool. %s') % e)
        if m == 'member':
            for obj_id in obj_ids:
                try:
                    api.lbaas.member_delete(request, obj_id)
                    messages.success(request, _('Deleted member %s') % obj_id)
                except Exception as e:
                    exceptions.handle(request,
                                      _('Unable to delete member. %s') % e)
        if m == 'vip':
            for obj_id in obj_ids:
                try:
                    vip_id = api.lbaas.pool_get(request, obj_id).vip_id
                except Exception as e:
                    exceptions.handle(request,
                                      _('Unable to locate VIP to delete. %s')
                                      % e)
                if vip_id is not None:
                    try:
                        api.lbaas.vip_delete(request, vip_id)
                        messages.success(request, _('Deleted VIP %s') % vip_id)

                    except Exception as e:
                        exceptions.handle(request,
                                          _('Unable to delete VIP. %s') % e)
        if m=='loadbalancer':
            for obj_id in obj_ids:
                try:
                    pool = api.lbaas.pool_get(request, obj_id)
                except Exception as e:
                    exceptions.handle(request,
                                      _('Unable to locate Loadbalancer to delete. %s')
                                      % e)
                # delete vip
                vip_id = pool.vip_id
                if vip_id is not None:
                    try:
                        api.lbaas.vip_delete(request, vip_id)
                    except Exception as e:
                        exceptions.handle(request,
                                          _('Unable to delete VIP. %s') % e)
                # delete pool
                try:
                    api.lbaas.pool_delete(request, obj_id)
                except Exception as e:
                    exceptions.handle(request,
                                      _('Unable to delete pool. %s') % e)
                # delete monitors
                monitors = pool.health_monitors
                if monitors is not None:
                    for mon in monitors:
                        try:
                            api.lbaas.pool_health_monitor_delete(request, mon.id)
                        except Exception as e:
                            exceptions.handle(request,
                                              _('Unable to delete monitor. %s') % e)
                messages.success(request, _('Deleted loadbalancer %s') % obj_id)

                # operation log

                api.logger.Logger(request).create(resource_type='loadblance', action_name='Delete Loadblance',
                                                       resource_name='Loadblance', config='',
                                                       status='Success')

        return self.get(request, *args, **kwargs)


class AddPoolView(workflows.WorkflowView):
    workflow_class = project_workflows.AddPool


class AddVipView(workflows.WorkflowView):
    workflow_class = project_workflows.AddVip

    def get_initial(self):
        initial = super(AddVipView, self).get_initial()
        initial['pool_id'] = self.kwargs['pool_id']
        try:
            pool = api.lbaas.pool_get(self.request, initial['pool_id'])
            initial['subnet'] = api.neutron.subnet_get(
                self.request, pool.subnet_id).cidr
        except Exception as e:
            initial['subnet'] = ''
            msg = _('Unable to retrieve pool subnet. %s') % e
            exceptions.handle(self.request, msg)
        return initial


class AddMemberView(workflows.WorkflowView):
    workflow_class = project_workflows.AddMember


class AddMonitorView(workflows.WorkflowView):
    workflow_class = project_workflows.AddMonitor


class PoolDetailsView(tabs.TabView):
    tab_group_class = project_tabs.PoolDetailsTabs
    template_name = 'network/loadbalancers/details_tabs.html'

    @memoized.memoized_method
    def get_data(self):
        pid = self.kwargs['pool_id']

        try:
            pool = api.lbaas.pool_get(self.request, pid)
        except Exception:
            pool = []
            exceptions.handle(self.request,
                              _('Unable to retrieve pool details.'))
        else:
            for monitor in pool.health_monitors:
                display_name = utils.get_monitor_display_name(monitor)
                setattr(monitor, 'display_name', display_name)

        return pool

    def get_context_data(self, **kwargs):
        context = super(PoolDetailsView, self).get_context_data(**kwargs)
        pool = self.get_data()
        context['pool'] = pool
        table = project_tables.PoolsTable(self.request)
        context["url"] = self.get_redirect_url()
        context["actions"] = table.render_row_actions(pool)
        return context

    def get_tabs(self, request, *args, **kwargs):
        pool = self.get_data()
        return self.tab_group_class(self.request, pool=pool, **kwargs)

    @staticmethod
    def get_redirect_url():
        return reverse_lazy("horizon:network:loadbalancers:index")


class VipDetailsView(tabs.TabView):
    tab_group_class = project_tabs.VipDetailsTabs
    template_name = 'network/loadbalancers/details_tabs.html'


class MemberDetailsView(tabs.TabView):
    tab_group_class = project_tabs.MemberDetailsTabs
    template_name = 'network/loadbalancers/details_tabs.html'

    @memoized.memoized_method
    def get_data(self):
        mid = self.kwargs['member_id']
        try:
            return api.lbaas.member_get(self.request, mid)
        except Exception:
            exceptions.handle(self.request,
                              _('Unable to retrieve member details.'))

    def get_context_data(self, **kwargs):
        context = super(MemberDetailsView, self).get_context_data(**kwargs)
        member = self.get_data()
        context['member'] = member
        table = project_tables.MembersTable(self.request)
        context["url"] = self.get_redirect_url()
        context["actions"] = table.render_row_actions(member)
        return context

    def get_tabs(self, request, *args, **kwargs):
        member = self.get_data()
        return self.tab_group_class(request, member=member, **kwargs)

    @staticmethod
    def get_redirect_url():
        return reverse_lazy("horizon:network:loadbalancers:index")


class MonitorDetailsView(tabs.TabView):
    tab_group_class = project_tabs.MonitorDetailsTabs
    template_name = 'network/loadbalancers/details_tabs.html'

    @memoized.memoized_method
    def get_data(self):
        mid = self.kwargs['monitor_id']
        try:
            return api.lbaas.pool_health_monitor_get(self.request, mid)
        except Exception:
            exceptions.handle(self.request,
                              _('Unable to retrieve monitor details.'))

    def get_context_data(self, **kwargs):
        context = super(MonitorDetailsView, self).get_context_data(**kwargs)
        monitor = self.get_data()
        context['monitor'] = monitor
        table = project_tables.MonitorsTable(self.request)
        context["url"] = self.get_redirect_url()
        context["actions"] = table.render_row_actions(monitor)
        return context

    def get_tabs(self, request, *args, **kwargs):
        monitor = self.get_data()
        return self.tab_group_class(request, monitor=monitor, **kwargs)

    @staticmethod
    def get_redirect_url():
        return reverse_lazy("horizon:network:loadbalancers:index")


class LoadBalancerDetailsView(tabs.TabView):
    tab_group_class = project_tabs.LoadBalancerDetailsTabs
    template_name = 'network/loadbalancers/details_tabs.html'

    @memoized.memoized_method
    def get_data(self):
        pid = self.kwargs['pool_id']

        try:
            pool = api.lbaas.pool_get(self.request, pid)
        except Exception:
            pool = []
            exceptions.handle(self.request,
                              _('Unable to retrieve loadbalancer details.'))
        if pool.vip_id:
            vip = api.lbaas.vip_get(self.request, pool.vip_id)
            fips = api.network.tenant_floating_ip_list(self.request)
            vip_fip = [fip for fip in fips
                       if fip.port_id == vip.port_id]
        if vip_fip:
            pool._apidict['floating_ip'] = vip_fip[0].floating_ip_address
        else:
            for monitor in pool.health_monitors:
                display_name = utils.get_monitor_display_name(monitor)
                setattr(monitor, 'display_name', display_name)

        return pool

    def get_context_data(self, **kwargs):
        context = super(LoadBalancerDetailsView, self).get_context_data(**kwargs)
        pool = self.get_data()
        context['pool'] = pool
        table = project_tables.LoadBalancersTable(self.request)
        context["url"] = self.get_redirect_url()
        context["actions"] = table.render_row_actions(pool)
        return context

    def get_tabs(self, request, *args, **kwargs):
        pool = self.get_data()
        return self.tab_group_class(self.request, pool=pool, **kwargs)

    @staticmethod
    def get_redirect_url():
        return reverse_lazy("horizon:network:loadbalancers:index")


class UpdatePoolView(forms.ModalFormView):
    form_class = project_forms.UpdatePool
    form_id = "update_pool_form"
    modal_header = _("Edit Pool")
    template_name = "network/loadbalancers/updatepool.html"
    context_object_name = 'pool'
    submit_label = _("Save Changes")
    submit_url = "horizon:network:loadbalancers:updatepool"
    success_url = reverse_lazy("horizon:network:loadbalancers:index")
    page_title = _("Edit Pool")

    def get_context_data(self, **kwargs):
        context = super(UpdatePoolView, self).get_context_data(**kwargs)
        context["pool_id"] = self.kwargs['pool_id']
        args = (self.kwargs['pool_id'],)
        context['submit_url'] = reverse(self.submit_url, args=args)
        return context

    @memoized.memoized_method
    def _get_object(self, *args, **kwargs):
        pool_id = self.kwargs['pool_id']
        try:
            return api.lbaas.pool_get(self.request, pool_id)
        except Exception as e:
            redirect = self.success_url
            msg = _('Unable to retrieve loadbalancer details. %s') % e
            exceptions.handle(self.request, msg, redirect=redirect)

    def get_initial(self):
        pool = self._get_object()
        return {'name': pool['name'],
                'pool_id': pool['id'],
                'description': pool['description'],
                'lb_method': pool['lb_method'],
                'admin_state_up': pool['admin_state_up']}


class UpdateVipView(forms.ModalFormView):
    form_class = project_forms.UpdateVip
    form_id = "update_vip_form"
    modal_header = _("Edit VIP")
    template_name = "network/loadbalancers/updatevip.html"
    context_object_name = 'vip'
    submit_label = _("Save Changes")
    submit_url = "horizon:network:loadbalancers:updatevip"
    success_url = reverse_lazy("horizon:network:loadbalancers:index")
    page_title = _("Edit VIP")

    def get_context_data(self, **kwargs):
        context = super(UpdateVipView, self).get_context_data(**kwargs)
        context["vip_id"] = self.kwargs['vip_id']
        args = (self.kwargs['vip_id'],)
        context['submit_url'] = reverse(self.submit_url, args=args)
        return context

    @memoized.memoized_method
    def _get_object(self, *args, **kwargs):
        vip_id = self.kwargs['vip_id']
        try:
            return api.lbaas.vip_get(self.request, vip_id)
        except Exception as e:
            redirect = self.success_url
            msg = _('Unable to retrieve VIP details. %s') % e
            exceptions.handle(self.request, msg, redirect=redirect)

    def get_initial(self):
        vip = self._get_object()
        persistence = getattr(vip, 'session_persistence', None)
        if persistence:
            stype = persistence['type']
            if stype == 'APP_COOKIE':
                cookie = persistence['cookie_name']
            else:
                cookie = ''
        else:
            stype = ''
            cookie = ''

        return {'name': vip['name'],
                'vip_id': vip['id'],
                'description': vip['description'],
                'pool_id': vip['pool_id'],
                'session_persistence': stype,
                'cookie_name': cookie,
                'connection_limit': vip['connection_limit'],
                'admin_state_up': vip['admin_state_up']}


class UpdateMemberView(forms.ModalFormView):
    form_class = project_forms.UpdateMember
    form_id = "update_pool_form"
    modal_header = _("Edit Member")
    template_name = "network/loadbalancers/updatemember.html"
    context_object_name = 'member'
    submit_label = _("Save Changes")
    submit_url = "horizon:network:loadbalancers:updatemember"
    success_url = reverse_lazy("horizon:network:loadbalancers:index")
    page_title = _("Edit Member")

    def get_context_data(self, **kwargs):
        context = super(UpdateMemberView, self).get_context_data(**kwargs)
        context["member_id"] = self.kwargs['member_id']
        args = (self.kwargs['member_id'],)
        context['submit_url'] = reverse(self.submit_url, args=args)
        return context

    @memoized.memoized_method
    def _get_object(self, *args, **kwargs):
        member_id = self.kwargs['member_id']
        try:
            return api.lbaas.member_get(self.request, member_id)
        except Exception as e:
            redirect = self.success_url
            msg = _('Unable to retrieve member details. %s') % e
            exceptions.handle(self.request, msg, redirect=redirect)

    def get_initial(self):
        member = self._get_object()
        return {'member_id': member['id'],
                'pool_id': member['pool_id'],
                'weight': member['weight'],
                'admin_state_up': member['admin_state_up']}


class UpdateMonitorView(forms.ModalFormView):
    form_class = project_forms.UpdateMonitor
    form_id = "update_monitor_form"
    modal_header = _("Edit Monitor")
    template_name = "network/loadbalancers/updatemonitor.html"
    context_object_name = 'monitor'
    submit_label = _("Save Changes")
    submit_url = "horizon:network:loadbalancers:updatemonitor"
    success_url = reverse_lazy("horizon:network:loadbalancers:index")
    page_title = _("Edit Monitor")

    def get_context_data(self, **kwargs):
        context = super(UpdateMonitorView, self).get_context_data(**kwargs)
        context["monitor_id"] = self.kwargs['monitor_id']
        args = (self.kwargs['monitor_id'],)
        context['submit_url'] = reverse(self.submit_url, args=args)
        return context

    @memoized.memoized_method
    def _get_object(self, *args, **kwargs):
        monitor_id = self.kwargs['monitor_id']
        try:
            return api.lbaas.pool_health_monitor_get(self.request, monitor_id)
        except Exception as e:
            redirect = self.success_url
            msg = _('Unable to retrieve health monitor details. %s') % e
            exceptions.handle(self.request, msg, redirect=redirect)

    def get_initial(self):
        monitor = self._get_object()
        return {'monitor_id': monitor['id'],
                'delay': monitor['delay'],
                'timeout': monitor['timeout'],
                'max_retries': monitor['max_retries'],
                'admin_state_up': monitor['admin_state_up']}


class AddPMAssociationView(workflows.WorkflowView):
    workflow_class = project_workflows.AddPMAssociation

    def get_initial(self):
        initial = super(AddPMAssociationView, self).get_initial()
        initial['pool_id'] = self.kwargs['pool_id']
        try:
            pool = api.lbaas.pool_get(self.request, initial['pool_id'])
            initial['pool_name'] = pool.name
            initial['pool_monitors'] = pool.health_monitors
        except Exception as e:
            msg = _('Unable to retrieve pool. %s') % e
            exceptions.handle(self.request, msg)
        return initial


class DeletePMAssociationView(workflows.WorkflowView):
    workflow_class = project_workflows.DeletePMAssociation

    def get_initial(self):
        initial = super(DeletePMAssociationView, self).get_initial()
        initial['pool_id'] = self.kwargs['pool_id']
        try:
            pool = api.lbaas.pool_get(self.request, initial['pool_id'])
            initial['pool_name'] = pool.name
            initial['pool_monitors'] = pool.health_monitors
        except Exception as e:
            msg = _('Unable to retrieve pool. %s') % e
            exceptions.handle(self.request, msg)
        return initial


class AddLoadBalancerView(workflows.WorkflowView):
    workflow_class = project_workflows.AddLoadBalancer


class UpdateLoadBalancerView(forms.ModalFormView):
    form_class = project_forms.UpdateLoadBalancer
    form_id = "update_loadbalancer_form"
    modal_header = _("Edit LoadBalancer")
    template_name = "network/loadbalancers/updateloadbalancer.html"
    context_object_name = 'loadbalancer'
    submit_label = _("Save Changes")
    submit_url = "horizon:network:loadbalancers:updateloadbalancer"
    success_url = reverse_lazy("horizon:network:loadbalancers:index")
    page_title = _("Edit LoadBalancer")

    def get_context_data(self, **kwargs):
        context = super(UpdateLoadBalancerView, self).get_context_data(**kwargs)
        context["pool_id"] = self.kwargs['pool_id']
        args = (self.kwargs['pool_id'],)
        context['submit_url'] = reverse(self.submit_url, args=args)
        return context

    @memoized.memoized_method
    def _get_object(self, *args, **kwargs):
        pool_id = self.kwargs['pool_id']
        try:
            return api.lbaas.pool_get(self.request, pool_id)
        except Exception as e:
            redirect = self.success_url
            msg = _('Unable to retrieve loadbalancer details. %s') % e
            exceptions.handle(self.request, msg, redirect=redirect)

    def get_initial(self):
        pool = self._get_object()

        vip = pool.vip

        persistence = getattr(vip, 'session_persistence', None)
        if persistence:
            stype = persistence['type']
            if stype == 'APP_COOKIE':
                cookie = persistence['cookie_name']
            else:
                cookie = ''
        else:
            stype = ''
            cookie = ''

        set_health_check = False
        monitor = {}
        if len(pool.health_monitors) > 0:
            set_health_check = True
            monitor = pool.health_monitors[0]
            if monitor.type == "PING" or  monitor.type == "TCP" :
                monitor._apidict['url_path'] = ''
        else:
            monitor['id'] = ''
            monitor['delay'] = ''
            monitor['timeout'] = ''
            monitor['max_retries'] = ''
            monitor['type'] = ''
            monitor['url_path'] = ''
        return  {'pool_id': pool['id'],
                'name': pool['name'],
                'protocol': pool['protocol'],
                'lb_method': pool['lb_method'],
                'vip_id': vip['id'],
                'protocol_port': vip['protocol_port'],
                'session_persistence': stype,
                'cookie_name': cookie,
                'connection_limit': vip['connection_limit'],
                'set_health_check': set_health_check,
                'monitor_id':  monitor['id'],
                'type' : monitor['type'].lower(),
                'delay': monitor['delay'],
                'timeout': monitor['timeout'],
                'max_retries': monitor['max_retries'],
                'url_path': monitor['url_path']}


class BackendServerView(workflows.WorkflowView):
    workflow_class = project_workflows.BackendServer

    def get_initial(self):
        pool_id = self.kwargs['pool_id']
        return {'pool_id': pool_id}
