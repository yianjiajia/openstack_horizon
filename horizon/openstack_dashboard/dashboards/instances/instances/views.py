# Copyright 2012 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
#
# Copyright 2012 Nebula, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
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
Views for managing instances.
"""
import logging
from django.http import HttpResponse
from django.core.urlresolvers import reverse
from django.core.urlresolvers import reverse_lazy
from django import http
from django import shortcuts
from django.utils.datastructures import SortedDict
from django.utils.translation import ugettext_lazy as _
from django.views import generic

from horizon import exceptions
from horizon import forms
from horizon import messages
from horizon import tables
from horizon import tabs
from horizon.utils import memoized
from horizon import workflows

from openstack_dashboard import api

from openstack_dashboard.dashboards.instances.instances \
    import console as project_console
from openstack_dashboard.dashboards.instances.instances \
    import forms as project_forms
from openstack_dashboard.dashboards.instances.instances \
    import tables as project_tables
from openstack_dashboard.dashboards.instances.instances \
    import tabs as project_tabs
from openstack_dashboard.dashboards.instances.instances \
    import workflows as project_workflows

from openstack_dashboard.dashboards.instances.instances.tables import STATUS_DISPLAY_CHOICES
from openstack_dashboard.usage import quotas


LOG = logging.getLogger(__name__)


class IndexView(tables.DataTableView):
    table_class = project_tables.InstancesTable
    template_name = 'instances/instances/index.html'
    page_title = _("Instances")

    def has_more_data(self, table):
        return self._more

    def get_data(self):
        marker = self.request.GET.get(
            project_tables.InstancesTable._meta.pagination_param, None)
        search_opts = self.get_filters({'marker': marker, 'paginate': True})
        # Gather our instances
        try:
            instances, self._more = api.nova.server_list(
                self.request,
                search_opts=search_opts)
        except Exception:
            self._more = False
            instances = []
            exceptions.handle(self.request,
                              _('Unable to retrieve instances.'))
        # if instances:
        #     try:
        #         api.network.servers_update_addresses(self.request, instances)
        #     except Exception:
        #         exceptions.handle(
        #             self.request,
        #             message=_('Unable to retrieve IP addresses from Neutron.'),
        #             ignore=True)
        #
        #     # Gather our flavors and images and correlate our instances to them
        #     try:
        #         flavors = api.nova.flavor_list(self.request)
        #     except Exception:
        #         flavors = []
        #         exceptions.handle(self.request, ignore=True)
        #
        #     try:
        #         # TODO(gabriel): Handle pagination.
        #         images, more, prev = api.glance.image_list_detailed(
        #             self.request)
        #     except Exception:
        #         images = []
        #         exceptions.handle(self.request, ignore=True)
        #
        #     full_flavors = SortedDict([(str(flavor.id), flavor)
        #                                for flavor in flavors])
        #     image_map = SortedDict([(str(image.id), image)
        #                             for image in images])
        #
        #     # Loop through instances to get flavor info.
        #     for instance in instances:
        #         if hasattr(instance, 'image'):
        #             # Instance from image returns dict
        #             if isinstance(instance.image, dict):
        #                 if instance.image.get('id') in image_map:
        #                     instance.image = image_map[instance.image['id']]
        #
        #         try:
        #             flavor_id = instance.flavor["id"]
        #             if flavor_id in full_flavors:
        #                 instance.full_flavor = full_flavors[flavor_id]
        #             else:
        #                 # If the flavor_id is not in full_flavors list,
        #                 # get it via nova api.
        #                 instance.full_flavor = api.nova.flavor_get(
        #                     self.request, flavor_id)
        #         except Exception:
        #             msg = ('Unable to retrieve flavor "%s" for instance "%s".'
        #                    % (flavor_id, instance.id))
        #             LOG.info(msg)
        return instances

    def get_filters(self, filters):
        filter_action = self.table._meta._filter_action
        if filter_action:
            filter_field = self.table.get_filter_field()
            if filter_action.is_api_filter(filter_field):
                filter_string = self.table.get_filter_string()
                if filter_field == 'status' and filter_string and (0x4e00 <= ord(filter_string[0]) < 0x9fa6):
                    filter_string = [x[0] for x in STATUS_DISPLAY_CHOICES if x[1] == filter_string]
                    if filter_string:
                        filter_string = filter_string[0]
                    else:
                        filter_string = 'not_make_sense'
                if filter_field and filter_string:
                    filters[filter_field] = filter_string
        return filters

    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)
        account = api.billing.RequestClient(self.request).get_account()
        if account['status'] == 'frozen':
            context['account_is_frozen'] = 1
        else:
            context['account_is_frozen'] = 0
        return context


class LaunchInstanceView(workflows.WorkflowView):
    workflow_class = project_workflows.LaunchInstance
    template_name = 'instances/instances/_workflow_base.html'
    ajax_template_name = 'instances/instances/_workflow.html'

    def get_initial(self):
        initial = super(LaunchInstanceView, self).get_initial()
        initial['project_id'] = self.request.user.tenant_id
        initial['user_id'] = self.request.user.id
        return initial


def console(request, instance_id):
    data = _('Unable to get log for instance "%s".') % instance_id
    tail = request.GET.get('length')
    if tail and not tail.isdigit():
        msg = _('Log length must be a nonnegative integer.')
        messages.warning(request, msg)
    else:
        try:
            data = api.nova.server_console_output(request,
                                                  instance_id,
                                                  tail_length=tail)
        except Exception:
            exceptions.handle(request, ignore=True)
    return http.HttpResponse(data.encode('utf-8'), content_type='text/plain')


def vnc(request, instance_id):
    try:
        instance = api.nova.server_get(request, instance_id)
        console_url = project_console.get_console(request, 'VNC', instance)[1]
        return shortcuts.redirect(console_url)
    except Exception:
        redirect = reverse("horizon:instances:instances:index")
        msg = _('Unable to get VNC console for instance "%s".') % instance_id
        exceptions.handle(request, msg, redirect=redirect)


def spice(request, instance_id):
    try:
        instance = api.nova.server_get(request, instance_id)
        console_url = project_console.get_console(request, 'SPICE',
                                                  instance)[1]
        return shortcuts.redirect(console_url)
    except Exception:
        redirect = reverse("horizon:instances:instances:index")
        msg = _('Unable to get SPICE console for instance "%s".') % instance_id
        exceptions.handle(request, msg, redirect=redirect)


def rdp(request, instance_id):
    try:
        instance = api.nova.server_get(request, instance_id)
        console_url = project_console.get_console(request, 'RDP', instance)[1]
        return shortcuts.redirect(console_url)
    except Exception:
        redirect = reverse("horizon:instances:instances:index")
        msg = _('Unable to get RDP console for instance "%s".') % instance_id
        exceptions.handle(request, msg, redirect=redirect)


class SerialConsoleView(generic.TemplateView):
    template_name = 'instances/instances/serial_console.html'

    def get_context_data(self, **kwargs):
        context = super(SerialConsoleView, self).get_context_data(**kwargs)
        context['instance_id'] = self.kwargs['instance_id']
        instance = None
        try:
            instance = api.nova.server_get(self.request,
                                           self.kwargs['instance_id'])
        except Exception:
            context["error_message"] = _(
                "Cannot find instance %s.") % self.kwargs['instance_id']
            # name is unknown, so leave it blank for the window title
            # in full-screen mode, so only the instance id is shown.
            context['instance_name'] = ''
            return context
        context['instance_name'] = instance.name
        try:
            console_url = project_console.get_console(self.request,
                                                      "SERIAL", instance)[1]
            context["console_url"] = console_url
        except exceptions.NotAvailable:
            context["error_message"] = _(
                "Cannot get console for instance %s.") % self.kwargs[
                'instance_id']
        return context


class UpdateView(workflows.WorkflowView):
    workflow_class = project_workflows.UpdateInstance
    success_url = reverse_lazy("horizon:instances:instances:index")

    def get_context_data(self, **kwargs):
        context = super(UpdateView, self).get_context_data(**kwargs)
        context["instance_id"] = self.kwargs['instance_id']
        return context

    @memoized.memoized_method
    def get_object(self, *args, **kwargs):
        instance_id = self.kwargs['instance_id']
        try:
            return api.nova.server_get(self.request, instance_id)
        except Exception:
            redirect = reverse("horizon:instances:instances:index")
            msg = _('Unable to retrieve instance details.')
            exceptions.handle(self.request, msg, redirect=redirect)

    def get_initial(self):
        initial = super(UpdateView, self).get_initial()
        initial.update({'instance_id': self.kwargs['instance_id'],
                        'name': getattr(self.get_object(), 'name', '')})
        return initial


class RebuildView(forms.ModalFormView):
    form_class = project_forms.RebuildInstanceForm
    template_name = 'instances/instances/rebuild.html'
    success_url = reverse_lazy('horizon:instances:instances:index')
    page_title = _("Rebuild Instance")

    def get_context_data(self, **kwargs):
        context = super(RebuildView, self).get_context_data(**kwargs)
        context['instance_id'] = self.kwargs['instance_id']
        context['can_set_server_password'] = api.nova.can_set_server_password()
        return context

    def get_initial(self):
        return {'instance_id': self.kwargs['instance_id']}


class ResetPasswordView(workflows.WorkflowView):
    workflow_class = project_workflows.ResetPassword
    success_url = reverse_lazy("horizon:instances:instances:index")

    def get_context_data(self, **kwargs):
        context = super(ResetPasswordView, self).get_context_data(**kwargs)
        context["instance_id"] = self.kwargs['instance_id']
        return context

    @memoized.memoized_method
    def get_object(self, *args, **kwargs):
        instance_id = self.kwargs['instance_id']
        try:
            return api.nova.server_get(self.request, instance_id)
        except Exception:
            redirect = reverse("horizon:instances:instances:index")
            msg = _('Unable to retrieve instance details.')
            exceptions.handle(self.request, msg, redirect=redirect)

    def get_initial(self):
        initial = super(ResetPasswordView, self).get_initial()
        instance = self.get_object()

        is_allow_inject_passwd = False
        image_name = None
        image_id = getattr(instance, 'image', {}).get('id', None)
        if image_id:
            image = api.glance.image_get(self.request, image_id)
            image_name = getattr(image, 'name', None)
            is_allow_inject_passwd = getattr(image, 'is_allow_inject_passwd', False)

        initial.update({'instance_id': self.kwargs['instance_id'],
                        'name': getattr(instance, 'name', ''),
                        'image_name': image_name,
                        'is_allow_inject_passwd': is_allow_inject_passwd})
        return initial


class DecryptPasswordView(forms.ModalFormView):
    form_class = project_forms.DecryptPasswordInstanceForm
    template_name = 'instances/instances/decryptpassword.html'
    success_url = reverse_lazy('horizon:instances:instances:index')
    page_title = _("Retrieve Instance Password")

    def get_context_data(self, **kwargs):
        context = super(DecryptPasswordView, self).get_context_data(**kwargs)
        context['instance_id'] = self.kwargs['instance_id']
        context['keypair_name'] = self.kwargs['keypair_name']
        return context

    def get_initial(self):
        return {'instance_id': self.kwargs['instance_id'],
                'keypair_name': self.kwargs['keypair_name']}


class DetailView(tabs.TabView):
    tab_group_class = project_tabs.InstanceDetailTabs
    template_name = 'instances/instances/detail.html'
    redirect_url = 'horizon:instances:instances:index'
    page_title = _("Instance Details")

    def get_context_data(self, **kwargs):
        context = super(DetailView, self).get_context_data(**kwargs)
        instance = self.get_data()
        context["instance"] = instance
        table = project_tables.InstancesTable(self.request)
        context["url"] = reverse(self.redirect_url)
        context["actions"] = table.render_row_actions(instance)
        return context

    @memoized.memoized_method
    def get_data(self):
        instance_id = self.kwargs['instance_id']

        try:
            instance = api.nova.server_get(self.request, instance_id)
        except Exception:
            redirect = reverse(self.redirect_url)
            exceptions.handle(self.request,
                              _('Unable to retrieve details for '
                                'instance "%s".') % instance_id,
                              redirect=redirect)
            # Not all exception types handled above will result in a redirect.
            # Need to raise here just in case.
            raise exceptions.Http302(redirect)

        status_label = [label for (value, label) in
                        project_tables.STATUS_DISPLAY_CHOICES
                        if value.lower() == (instance.status or '').lower()]
        if status_label:
            instance.status_label = status_label[0]
        else:
            instance.status_label = instance.status

        try:
            instance.volumes = api.nova.instance_volumes_list(self.request,
                                                              instance_id)
            # Sort by device name
            instance.volumes.sort(key=lambda vol: vol.device)
        except Exception:
            msg = _('Unable to retrieve volume list for instance '
                    '"%(name)s" (%(id)s).') % {'name': instance.name,
                                               'id': instance_id}
            exceptions.handle(self.request, msg, ignore=True)

        try:
            instance.full_flavor = api.nova.flavor_get(
                self.request, instance.flavor["id"])
        except Exception:
            msg = _('Unable to retrieve flavor information for instance '
                    '"%(name)s" (%(id)s).') % {'name': instance.name,
                                               'id': instance_id}
            exceptions.handle(self.request, msg, ignore=True)

        try:
            instance.security_groups = api.network.server_security_groups(
                self.request, instance_id)
        except Exception:
            msg = _('Unable to retrieve security groups for instance '
                    '"%(name)s" (%(id)s).') % {'name': instance.name,
                                               'id': instance_id}
            exceptions.handle(self.request, msg, ignore=True)

        try:
            api.network.servers_update_addresses(self.request, [instance])
        except Exception:
            msg = _('Unable to retrieve IP addresses from Neutron for '
                    'instance "%(name)s" (%(id)s).') % {'name': instance.name,
                                                        'id': instance_id}
            exceptions.handle(self.request, msg, ignore=True)

        return instance

    def get_tabs(self, request, *args, **kwargs):
        instance = self.get_data()
        return self.tab_group_class(request, instance=instance, **kwargs)


class ResizeView(workflows.WorkflowView):
    workflow_class = project_workflows.ResizeInstance
    success_url = reverse_lazy("horizon:instances:instances:index")

    def get_context_data(self, **kwargs):
        context = super(ResizeView, self).get_context_data(**kwargs)
        context["instance_id"] = self.kwargs['instance_id']
        return context

    @memoized.memoized_method
    def get_object(self, *args, **kwargs):
        instance_id = self.kwargs['instance_id']
        try:
            instance = api.nova.server_get(self.request, instance_id)
        except Exception:
            redirect = reverse("horizon:instances:instances:index")
            msg = _('Unable to retrieve instance details.')
            exceptions.handle(self.request, msg, redirect=redirect)
        flavor_id = instance.flavor['id']
        flavors = self.get_flavors()
        if flavor_id in flavors:
            instance.flavor_name = flavors[flavor_id].name
        else:
            try:
                flavor = api.nova.flavor_get(self.request, flavor_id)
                instance.flavor_name = flavor.name
            except Exception:
                msg = _('Unable to retrieve flavor information for instance '
                        '"%s".') % instance_id
                exceptions.handle(self.request, msg, ignore=True)
                instance.flavor_name = _("Not available")
        return instance

    @memoized.memoized_method
    def get_flavors(self, *args, **kwargs):
        try:
            flavors = api.nova.flavor_list(self.request)
            return SortedDict((str(flavor.id), flavor) for flavor in flavors)
        except Exception:
            redirect = reverse("horizon:instances:instances:index")
            exceptions.handle(self.request,
                              _('Unable to retrieve flavors.'),
                              redirect=redirect)

    def get_initial(self):
        initial = super(ResizeView, self).get_initial()
        _object = self.get_object()
        if _object:
            initial.update(
                {'instance_id': self.kwargs['instance_id'],
                 'name': getattr(_object, 'name', None),
                 #'old_flavor_id': _object.flavor['id'],
                 #'old_flavor_name': getattr(_object, 'flavor_name', ''),
                 #'flavors': self.get_flavors()
                 'old_vcpus': getattr(_object, 'vcpus', None),
                 'old_memory_mb': getattr(_object, 'memory_mb', None),
                 })
        return initial


# instances API
def get_quota(request):
        usages = quotas.tenant_quota_usages(request)
        hdd_usages = quotas.tenant_limit_usages(request)
        available_float_ip = usages['floating_ips']['available']
        availableGB = hdd_usages['maxTotalVolumeGigabytes'] - hdd_usages['totalVolumeGigabytesUsed']
        availableVol = hdd_usages['maxTotalVolumes'] - hdd_usages['totalVolumesUsed']
        available_count = usages['instances']['available']
        available_cores = usages['cores']['available']
        available_ram = usages['ram']['available']
        return {
            'count': available_count,
            'vcpus': available_cores,
            'memory': available_ram,
            'float_ip': available_float_ip,
            'hdd_count': availableVol,
            'hdd': availableGB,
        }


def ajax_api(request):
    try:
        image_id = request.GET.get('image_id')
        if image_id:
            image = api.glance.image_get(request, image_id)
            image_json = {}
            image_json['min_disk'] = getattr(image, 'min_disk', None)
            image_json['is_allow_inject_passwd'] = (1 if getattr(image, 'is_allow_inject_passwd', False) else 0)
            return HttpResponse(repr(image_json))

        callback = request.GET.get('callback')
        if callback:
            image_list = api.glance.image_list_detailed(request)
            data = [[i.id.encode("utf-8"), i.name.encode("utf-8")] for i in image_list[0] if not i.is_public]
            return HttpResponse(callback+'('+str(data)+');', content_type='application/json')

        avl = request.GET.get('avl')
        if avl:
            value = get_quota(request)
            return HttpResponse(repr(value))

        instance_id = request.GET.get('instance_id')
        if instance_id:
            volumes = api.nova.instance_volumes_list(request, instance_id)
            snapshots = api.cinder.volume_snapshot_list(request)
            boot_gb = {}
            boot_gb['boot_gb'] = 0
            boot_gb['has_child'] = 0
            for volume in volumes:
                volume = api.cinder.volume_get(request, volume.id)
                bootable = getattr(volume, 'bootable', False)
                if bootable:
                    size = getattr(volume, 'size', 0)
                    boot_gb['boot_gb'] = size
                    for snapshot in snapshots:
                        if snapshot.volume_id == volume.id:
                            boot_gb['has_child'] = 1
                    break
            return HttpResponse(repr(boot_gb))

        # billing item
        billing_item = request.GET.get('billing_item')
        if billing_item:
            billing_item = api.billing.BillingItem(request).billing_item()
            return HttpResponse(repr(billing_item))

        snap_billing = request.GET.get('snap_billing')
        if snap_billing:
            size = 0
            billing_item = api.billing.BillingItem(request).billing_item()
            snap_price = billing_item['snapshot_1_G']
            ret = api.nova.instance_volumes_list(request, snap_billing)
            for volume in ret:
                system_hdd = getattr(volume, 'size', None)
                size = size+system_hdd
            image_json = {}
            image_json['price'] = size * snap_price
            return HttpResponse(repr(image_json))

        volume_id = request.GET.get('volume_id')
        if volume_id:
            billing_item = api.billing.BillingItem(request).billing_item()
            snap_price = billing_item['snapshot_1_G']
            volume = api.cinder.volume_get(request, volume_id)
            image_json = {}
            image_json['price'] = volume.size * snap_price
            return HttpResponse(repr(image_json))

        resize_instance_id = request.GET.get('resize_instance')
        if resize_instance_id:
                size = 0
                billing_item = api.billing.BillingItem(request).billing_item()
                hdd_price = billing_item['disk_1_G']
                image_price = billing_item['image_1']
                instance_price = billing_item['instance_1']
                float_ip_price = billing_item['ip_1']
                instance = api.nova.server_get(request, resize_instance_id)
                float_num = len(instance.networks.get('network'))-1
                if not instance.image:
                    image_price = 0
                instance_volume = api.nova.instance_volumes_list(request, resize_instance_id)
                for volume in instance_volume:
                    system_hdd = getattr(volume, 'size', None)
                    size = size+system_hdd
                image_json = {}
                image_json['original_price'] = size*hdd_price+instance_price+image_price+float_num*float_ip_price
                image_json['billing_item'] = billing_item
                return HttpResponse(repr(image_json))
    except Exception:
        exceptions.handle(request)


# CREATE INSTANCES FROM ISV


class LaunchInstanceIsvView(workflows.WorkflowView):
    workflow_class = project_workflows.LaunchInstanceIsv
    template_name = 'instances/instances/_workflow_base.html'
    ajax_template_name = 'instances/instances/_workflow.html'

    def get_initial(self):
        initial = super(LaunchInstanceIsvView, self).get_initial()
        initial['project_id'] = self.request.user.tenant_id
        initial['user_id'] = self.request.user.id
        return initial

# Get billing item


