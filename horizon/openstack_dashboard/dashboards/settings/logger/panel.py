__author__ = 'gaga'

from django.utils.translation import ugettext_lazy as _

import horizon

from openstack_dashboard.dashboards.settings import dashboard


class Logger(horizon.Panel):
    name = _("Action Log")
    slug = 'logger'


dashboard.Settings.register(Logger)
