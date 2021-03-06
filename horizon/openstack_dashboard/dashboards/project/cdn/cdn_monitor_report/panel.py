from django.utils.translation import ugettext_lazy as _

import horizon

from openstack_dashboard.dashboards.project import dashboard


class CdnMonitorReport(horizon.Panel):
    name = _("Monitor Report")
    slug = "cdn.cdn_monitor_report"
    policy_rules = (('cdn', 'cdn:monitor_report'),)


dashboard.Cdn.register(CdnMonitorReport)
