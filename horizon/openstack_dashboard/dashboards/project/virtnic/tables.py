import logging

from django.core.urlresolvers import reverse
from django.utils.translation import pgettext_lazy
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext_lazy

from horizon import tables

from openstack_dashboard import api
from openstack_dashboard import policy


LOG = logging.getLogger(__name__)

class CreateVirtnic(tables.LinkAction):
    name = "create"
    verbose_name = _("Create Virtnic")
    url = "horizon:project:virtnic:create"
    classes = ("ajax-modal",)
    icon = "plus"
    policy_rules = (("virtnic", "create_virtnic"),)

    def allowed(self, request, datum=None):
#         usages = quotas.tenant_quota_usages(request)
#         if usages['routers']['available'] <= 0:
#             if "disabled" not in self.classes:
#                 self.classes = [c for c in self.classes] + ["disabled"]
#                 self.verbose_name = _("Create Router (Quota exceeded)")
#         else:
#             self.verbose_name = _("Create Router")
#             self.classes = [c for c in self.classes if c != "disabled"]

        return True


class DeleteVirtnic(policy.PolicyTargetMixin, tables.BatchAction):
    name = "virtnic"
    classes = ("btn-danger",)
    icon = "remove"
    policy_rules = (("virtnic", "virtnic:delete"),)
    help_text = _("Delete Virtnic are not recoverable.")
 
    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Delete Virtnic",
            u"Delete Virtnics",
            count
        )
 
    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Scheduled delete of Virtnic",
            u"Scheduled delete of Virtnics",
            count
        )
 
    def allowed(self, request, instance=None):
        return True
 
    def action(self, request, obj_id):
        api.neutron.port_delete(request, obj_id)

class BindingVirtnic(policy.PolicyTargetMixin, tables.LinkAction):
    name = "binding"
    verbose_name = _("Binding Virtnic To Server")
    url = "horizon:project:routers:binding"
    classes = ("ajax-modal",)
    icon = "pencil"
    policy_rules = (("network", "binding_virtnic"),)
    
    def allowed(self, request, instance=None):
        print 
        if instance and hasattr(instance, "device_owner"):
            if instance["device_owner"]=="" and hasattr(instance, "device_id"):
                if len(instance["device_id"])==0:
                    return True
        return False
    def get_link_url(self, port):
        base_url = reverse("horizon:project:virtnic:binding",
                           kwargs={'port_id': port.id})
        return base_url


class unBindingVirtnic(policy.PolicyTargetMixin, tables.BatchAction):
    name = "unbinding"
    classes = ("btn-danger",)
    icon = "remove"
    policy_rules = (("virtnic", "virtnic:delete"),)
    help_text = _("Unbinding Virtnic are not recoverable.")
    redirect_url="horizon:project:virtnic:index"
 
    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Unbinding Virtnic",
            u"Unbinding Virtnics",
            count
        )
 
    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Scheduled unbinding of Virtnic",
            u"Scheduled unbinding of Virtnics",
            count
        )
 
    def allowed(self, request, instance=None):
        if instance and hasattr(instance, "device_owner"):
            if instance["device_owner"]=="compute:nova" and hasattr(instance, "device_id"):
                if len(instance["device_id"])>0:
                    return True
        return False
 
    def action(self, request, obj_id):
        port=self.table.get_object_by_id(obj_id)
        if hasattr(port, "device_id"):
            api.nova.interface_detach(request,port["device_id"], obj_id)
            import time
            time.sleep(3)
            
    def get_success_url(self, request):
        return reverse(self.redirect_url)

class UpdateRow(tables.Row):
    ajax = True

    def get_data(self, request, obj_id):
        port = api.neutron.port_get(request, obj_id)
#         try:
#             instance.full_flavor = api.nova.flavor_get(request,
#                                                        instance.flavor["id"])
#         except Exception:
#             exceptions.handle(request,
#                               _('Unable to retrieve flavor information '
#                                 'for instance "%s".') % instance_id,
#                               ignore=True)
#         error = get_instance_error(instance)
#         if error:
#             messages.error(request, error)
        return port


def get_ip(port):
    if hasattr(port, "fixed_ips"):
        fixed_ips = port.fixed_ips
        if len(fixed_ips) > 0:
            ips = ''
            for fixed_ip in fixed_ips:
                ips = ips.join(fixed_ip['ip_address']).join("  ")
            return ips
    return _("Not available")

def getFloating_ip(port):
    if hasattr(port, "fix_floating_ip"):
        fix_floating_ip=port["fix_floating_ip"]
        return fix_floating_ip["floating_ip_address"]
    return None

def get_host(port):
    if hasattr(port, 'host'):
        if hasattr(port.host, 'name'):
            return port.host.name
    return port["device_id"]


def get_network(port):
    if hasattr(port, 'network'):
        if hasattr(port.network, 'name'):
            return port.network.name
    return port["network_id"]
    
    
class PortsFilterAction(tables.FilterAction):
    def filter(self, table, ports, filter_string):
        query = filter_string.lower()
        return [port for port in ports
                if query in port.name]


STATUS_DISPLAY_CHOICES = (
    ("ACTIVE", pgettext_lazy("Current status of a Virtnic", u"Active")),
    ("DOWN", pgettext_lazy("Current status of a Virtnic", u"Down")),
    ("ERROR", pgettext_lazy("Current status of a Virtnic", u"Error")),
)

class VirtnicTable(tables.DataTable):
    name = tables.Column("name_or_id",
                         link="horizon:project:virtnic:detail",
                         verbose_name=_("Name"))
    description = tables.Column("description",
                         verbose_name=_("Description"))
    inner_ip = tables.Column(get_ip,
                         verbose_name=_("Inner_ip"))
    floating_ip=tables.Column(getFloating_ip,
                         verbose_name=_("Floating_ip"))
    subnet = tables.Column(get_network,
                         verbose_name=_("Subnet"))
    host = tables.Column(get_host,
                         verbose_name=_("Host"))
    status = tables.Column('status',
                         status=True,  
                         verbose_name=_("Status"),
                         display_choices=STATUS_DISPLAY_CHOICES)
    created_at = tables.Column("created_at",
                         verbose_name=_("Created_at"))

    class Meta(object):
        name = "virtnics"
        verbose_name = _("Virtnics")
        status_columns = ["status"]
        row_class = UpdateRow
        table_actions = (CreateVirtnic, DeleteVirtnic,PortsFilterAction)
        row_actions = (BindingVirtnic,unBindingVirtnic)
