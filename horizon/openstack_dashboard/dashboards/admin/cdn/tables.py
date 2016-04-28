__author__ = 'yanjiajia'
from django.core import urlresolvers
from django.template.defaultfilters import floatformat  # noqa
from django.utils.translation import ugettext_lazy as _
from horizon import tables
from horizon.templatetags import sizeformat
from django.utils.translation import ungettext_lazy
from horizon import messages
import logging
from horizon import exceptions
from openstack_dashboard.dashboards.cdn.middware import DomainManage
from openstack_dashboard.dashboards.cdn.cdn_domain_manager.models import Domain



LOG = logging.getLogger(__name__)

# class CSVSummary(tables.LinkAction):
#     name = "csv_summary"
#     verbose_name = _("Export Report")
#     icon = "download"
#
#     def get_link_url(self, usage=None):
#         return self.table.kwargs['usage'].csv_link()

#
#
# class DomainDetailList(tables.LinkAction):
#     name = "DomainList"
#     verbose_name = _("Manager Domain")
#     url = "horizon:admin:cdn:detail"
#     icon = "cog"
#
#
# def get_tenant_link(datum):
#     view = "horizon:admin:cdn:tenant"
#     if datum.Project_id:
#         return urlresolvers.reverse(view, args=(datum.Project_id,))
#     else:
#         return None
#
#
# class GlobalUsageTable(tables.DataTable):
#     Project_name = tables.Column('Project_name', verbose_name=_("Project Name"),
#                                  link=get_tenant_link)
#     User_name = tables.Column('User_name', verbose_name=_("User Name"))
#     Cdn_count = tables.Column('Cdn_count', verbose_name=_("Domain Count"))
#     Total_Flow = tables.Column('Total_Flow', verbose_name=_("Total Flow"),
#                                filters=(lambda v: floatformat(v, 2), sizeformat.mb_float_format))
#     Total_Requests = tables.Column('Total_Requests', verbose_name=_("Total Requests"))
#     Time_Section = tables.Column('Time_Section',
#                                  verbose_name=_("Time Section"))
#
#     def get_object_id(self, datum):
#         return datum.Project_id
#
#     class Meta(object):
#         name = "global_usage"
#         hidden_title = True
#         verbose_name = _("Usage")
#         columns = ("Project_name", "User_name", "Cdn_count", "Total_Flow",
#                    "Total_Requests", "Time_Section")
#         table_actions = (DomainDetailList, )


class DisableDomain(tables.DeleteAction):
    name = 'Disable'

    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            _("Disable"),
            _("Disable"),
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            _("Disable"),
            _("Disable"),
            count
        )

    def allowed(self, request, domain=None):
        if domain is not None:
            return domain.domain_id

    def delete(self, request, obj_id):
        try:
            domain = Domain.objects.get(pk=obj_id)
            domain.status = 'inProgress'
            domain.save()
            api = DomainManage()
            api.disable(domain.domain_id)

        except Exception:
            name = self.table.get_object_display(obj_id)
            msg = _('Unable to disable domain %s') % name
            LOG.info(msg)
            messages.error(request, msg)
            exceptions.handle(request, msg)


class EnableDomain(tables.DeleteAction):
    name = 'Enable'

    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            _("Enable"),
            _("Enable"),
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            _("Enable"),
            _("Enable"),
            count
        )

    def allowed(self, request, domain=None):
       if domain is not None:
            return domain.domain_id

    def delete(self, request, obj_id):
        try:
            domain = Domain.objects.get(pk=obj_id)
            domain.status = 'inProgress'
            domain.save()
            api = DomainManage()
            api.enable(domain.domain_id)

        except Exception:
            name = self.table.get_object_display(obj_id)
            msg = _('Unable to enable domain %s') % name
            LOG.info(msg)
            messages.error(request, msg)
            exceptions.handle(request, msg)


class UpdateRow(tables.Row):
    ajax = True

    def get_data(self, request, id):
        domain_api = DomainManage()
        domain = Domain.objects.get(pk=id)
        cdn = domain_api.find(domainId=domain.domain_id)
        if domain.status != cdn.domain.status:
               domain.status = cdn.domain.status
               domain.Enable = _(cdn.domain.enabled)
               domain.save()
        return domain


def get_domain_id_link(datum):
    view = "horizon:admin:cdn:domain_detail"
    if datum.tenant_id and datum.domain_id:
        return urlresolvers.reverse(view, args=(datum.tenant_id, datum.domain_id))
    else:
        return None


def get_tenant_id_link(datum):
    view = "horizon:admin:cdn:tenant_detail"
    if datum.tenant_id:
        return urlresolvers.reverse(view, args=(datum.tenant_id,))
    else:
        return None


class CDNFilterAction(tables.FilterAction):
    name = 'filter_cdn'
    filter_type = "server"
    filter_choices = (('project_name', _("Project Name"), True),
                      ('domain_name', _("Domain Name"), True))


class AllDomain(tables.DataTable):
    STATUS_DISPLAY_CHOICES_A = (
        ("unverified", _("Unverified")),
        ("failed", _("Verify Failed")),
        ("addfailed", _("Accelerate Failed")),
        ("Deployed", _("Deployed")),
        ("inProgress", _("inProgress")),
        ("deleted", _("Disable")),
    )

    STATUS_CHOICES = (
                     ('unverified', True),
                     ('failed', False),
                     ('addfailed', False),
                     ('Deployed', True),
                     ('inProgress', None),
    )
    project_name = tables.Column('project_name', verbose_name=_("Project Name"), link=get_tenant_id_link)
    user_name = tables.Column('user_name', verbose_name=_("User Name"))
    domain_name = tables.Column('domain_name', verbose_name=_("Domain Name"), link=get_domain_id_link)
    domain_id = tables.Column('domain_id', verbose_name=_("Domain Id"))
    domain_cname = tables.Column('domain_cname', verbose_name=_("CNAME"))
    status = tables.Column('status', verbose_name=_("Status"), status=True, display_choices=STATUS_DISPLAY_CHOICES_A,
                            status_choices=STATUS_CHOICES)
    Enable = tables.Column('Enable', verbose_name=_("Enabled"))
    current_type = tables.Column('current_type', verbose_name=_("Current Type"))
    created_at = tables.Column('created_at', verbose_name=_("Create At"))
    error_log = tables.Column('error_log', verbose_name=_("Error Log"))
    xCncRequestId = tables.Column('xCncRequestId', verbose_name=_("Request ID"))

    class Meta(object):
        name = "domain_list"
        verbose_name = _("Domain List")
        status_columns = ["status"]
        row_class = UpdateRow
        table_actions = (CDNFilterAction, )
        row_actions = (EnableDomain, DisableDomain)

#
# class TenantCSVSummary(tables.LinkAction):
#     name = "csv_summary"
#     verbose_name = _("Export Report")
#     icon = "download"
#
#     def get_link_url(self, usage=None):
#         return self.table.kwargs['usage'].csv_link()


class TenantUsageFilter(tables.FilterAction):
    def filter(self, table, domains, filter_string):
        """domain filter"""
        query = filter_string.lower()
        return [router for router in domains
                if query in router.name.lower()]


class TenantUsageTable(tables.DataTable):
    date = tables.Column('date', verbose_name=_("Date"))
    top_io = tables.Column('top_io', verbose_name=_("IO(Mb/s)"), filters=(lambda v: floatformat(v, 2),))
    total_flow = tables.Column('total_flow', verbose_name=_("Total Flow"),
                               filters=(lambda v: floatformat(v, 2), sizeformat.mb_float_format))
    total_requests = tables.Column('total_requests', verbose_name=_("Requests"))

    def get_object_id(self, datum):
        return datum.date

    class Meta(object):
        name = "domain_global_usage"
        verbose_name = _("Domain Usage")
        columns = ("date", "top_io", "total_flow", 'total_requests')
        table_actions = (TenantUsageFilter,)
