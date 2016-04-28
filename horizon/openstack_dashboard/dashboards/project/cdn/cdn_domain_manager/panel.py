from django.utils.translation import ugettext_lazy as _

import horizon

from openstack_dashboard.dashboards.cdn import dashboard


class CdnDomainManager(horizon.Panel):
    name = _("Domain Manager")
    slug = "cdn_domain_manager"
    policy_rules = (('cdn', 'cdn:domain_manager'),)

dashboard.Cdn.register(CdnDomainManager)
