__author__ = 'yamin'

from django.utils.translation import ugettext_lazy as _

import horizon

from openstack_dashboard.dashboards.settings import dashboard


class WorkOrder(horizon.Panel):
    name = _("Work Order Management")
    slug = 'workorder'


dashboard.Settings.register(WorkOrder)
