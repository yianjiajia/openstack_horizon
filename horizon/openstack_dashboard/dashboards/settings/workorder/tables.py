__author__ = 'yamin'

from horizon import tables
from django.utils.translation import ugettext_lazy as _
from django.core import urlresolvers
from horizon.utils import filters

# def get_tenant_link(datum):
#     view = "horizon:identity:projects:detail"
#     if datum.project_id:
#         return urlresolvers.reverse(view, args=(datum.project_id,))
#     else:
#         return None

class CreateWorkOrder(tables.LinkAction):
    name = "create"
    verbose_name = _("Create Work Order")
    url = "horizon:settings:workorder:create"
    classes = ("ajax-modal",)
    icon = "plus"
    #policy_rules = (("compute", "compute_extension:keypairs:create"),)

    def allowed(self, request, datum):
        return True


class WorkOrderTable(tables.DataTable):
    workorderno = tables.Column("workorder_no", verbose_name=_("Work Order No"))
    applier=tables.Column("apply_by", verbose_name=_("Work Order Applier"))
    type = tables.Column("type", verbose_name=_("Work Order Type"))
    theme= tables.Column("theme", verbose_name=_("Work Order Theme"))
    description= tables.Column("content", verbose_name=_("Work Order Content"))
    apply_at= tables.Column("apply_at", verbose_name=_("Work Order Apply_at"))
    handled_at= tables.Column("lasthandled_at", verbose_name=_("Work Order Handled at"))
    handler= tables.Column("lasthandled_by", verbose_name=_("Work Order Handler"))
    status = tables.Column("status", verbose_name=_("Work Order Status"),)
    operate = tables.Column("operate", verbose_name=_("Work Order Operate"),)

    class Meta(object):
        name = "workorder"
        verbose_name = _("Work Order")
        table_actions = (CreateWorkOrder, )
        # row_actions = (DeleteKeyPairs,)