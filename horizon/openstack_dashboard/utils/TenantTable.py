from django.utils.translation import ugettext_lazy as _
from horizon import tables


class TenantIDTable(tables.DataTable):
    tenant_id = tables.Column("tenant_id", verbose_name=_("Project ID"))
