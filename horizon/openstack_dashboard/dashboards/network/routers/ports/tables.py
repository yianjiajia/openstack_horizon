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

import logging

from django.core.urlresolvers import reverse
from django.utils.translation import pgettext_lazy
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext_lazy

from horizon import exceptions
from horizon import tables
from horizon.utils.functions import check_account_is_frozen

from openstack_dashboard import api
from openstack_dashboard.dashboards.network.networks.ports \
    import tables as project_tables
from openstack_dashboard import policy

LOG = logging.getLogger(__name__)


def get_device_owner(port):
    if port['device_owner'] == 'network:router_gateway':
        return _('External Gateway')
    elif port['device_owner'] == 'network:router_interface':
        return _('Internal Interface')
    else:
        return ' '


class AddInterface(policy.PolicyTargetMixin, tables.LinkAction):
    name = "create"
    verbose_name = _("Add Interface")
    url = "horizon:network:routers:addinterface"
    classes = ("ajax-modal",)
    icon = "plus"
    policy_rules = (("network", "add_router_interface"),)

    def allowed(self, request, datum):
        account_is_frozen = check_account_is_frozen(request)
        if account_is_frozen:
            if "disabled" not in self.classes:
                self.classes = [c for c in self.classes] + ['disabled']
        else:
            self.classes = [c for c in self.classes if c != "disabled"]
        return super(AddInterface, self).allowed(request, datum)

    def get_link_url(self, datum=None):
        router_id = self.table.kwargs['router_id']
        return reverse(self.url, args=(router_id,))


class RemoveInterface(policy.PolicyTargetMixin, tables.DeleteAction):
    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Delete Interface",
            u"Delete Interfaces",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Deleted Interface",
            u"Deleted Interfaces",
            count
        )

    failure_url = 'horizon:network:routers:detail'
    policy_rules = (("network", "remove_router_interface"),)

    def delete(self, request, obj_id):
        try:
            router_id = self.table.kwargs['router_id']
            port = api.neutron.port_get(request, obj_id)
            if port['device_owner'] == 'network:router_gateway':
                api.neutron.router_remove_gateway(request, router_id)
            else:
                api.neutron.router_remove_interface(request,
                                                    router_id,
                                                    port_id=obj_id)

            # operation log
            config = _("Route ID: %s Port ID: %s") %(router_id, obj_id)
            api.logger.Logger(request).create(resource_type='route', action_name='Remove Interface',
                                                       resource_name='Route', config=config,
                                                       status='Success')
        except Exception:
            msg = _('Failed to delete interface %s') % obj_id
            LOG.info(msg)
            router_id = self.table.kwargs['router_id']
            redirect = reverse(self.failure_url,
                               args=[router_id])
            exceptions.handle(request, msg, redirect=redirect)

            # operation log
            api.logger.Logger(request).create(resource_type='route', action_name='Remove Interface',
                                                       resource_name='Route', config=_('Failed to delete interface %s') % obj_id,
                                                       status='Error')


DISPLAY_CHOICES = (
    ("UP", pgettext_lazy("Admin state of a Port", u"UP")),
    ("DOWN", pgettext_lazy("Admin state of a Port", u"DOWN")),
)
STATUS_DISPLAY_CHOICES = (
    ("ACTIVE", pgettext_lazy("current status of port", u"Active")),
    ("BUILD", pgettext_lazy("current status of port", u"Build")),
    ("DOWN", pgettext_lazy("current status of port", u"Down")),
    ("ERROR", pgettext_lazy("current status of port", u"Error")),
)


class PortsTable(tables.DataTable):
    name = tables.Column("name_or_id",
                         verbose_name=_("Name"),
                         link="horizon:network:networks:ports:detail")
    fixed_ips = tables.Column(project_tables.get_fixed_ips,
                              verbose_name=_("Fixed IPs"))
    status = tables.Column("status",
                           verbose_name=_("Status"),
                           display_choices=STATUS_DISPLAY_CHOICES)
    device_owner = tables.Column(get_device_owner,
                                 verbose_name=_("Type"))
    admin_state = tables.Column("admin_state",
                                verbose_name=_("Admin State"),
                                display_choices=DISPLAY_CHOICES)

    def get_object_display(self, port):
        return port.id

    class Meta(object):
        name = "interfaces"
        verbose_name = _("Interfaces")
        table_actions = (AddInterface, RemoveInterface)
        row_actions = (RemoveInterface, )
