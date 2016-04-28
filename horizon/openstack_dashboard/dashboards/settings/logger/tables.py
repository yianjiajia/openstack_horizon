__author__ = 'gaga'

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

def get_user_link(datum):
    view = "horizon:identity:account:detail"
    if datum.user_id:
        return urlresolvers.reverse(view, args=(datum.user_id,))
    else:
        return None


class LoggerTable(tables.DataTable):
    project_name = tables.Column("project_name", verbose_name=_("Project Name"))
    user_name = tables.Column("user_name", verbose_name=_("User Name"),
                            link=get_user_link,)
    action_name = tables.Column("action_name", verbose_name=_("Action Name"))
    resource_name = tables.Column("resource_name", verbose_name=_("Resource Name"))
    region = tables.Column("region", verbose_name=_("Region"))
    config = tables.Column("config", verbose_name=_("Config Details"))
    action_at = tables.Column("action_at", verbose_name=_("Action Time"),
                              filters=[filters.parse_isotime])
    status = tables.Column("status", verbose_name=_("Status"))

    class Meta(object):
        name = "logger"
        verbose_name = _("Logger")
