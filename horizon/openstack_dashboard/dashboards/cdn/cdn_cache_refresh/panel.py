from django.utils.translation import ugettext_lazy as _

import horizon

from openstack_dashboard.dashboards.cdn import dashboard


class CdnCacheRefresh(horizon.Panel):
    name = _("Cache Fresh")
    slug = "cdn_cache_refresh"
    policy_rules = (('cdn', 'cdn:cache_refresh'),)

dashboard.Cdn.register(CdnCacheRefresh)
