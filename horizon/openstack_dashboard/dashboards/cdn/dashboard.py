__author__ = 'gaga'
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
import horizon


class Cdn(horizon.Dashboard):
    name = _("CDN")
    slug = "cdn"
    default_panel = "cdn_domain_manager"
    panels = ('cdn_domain_manager',
              'cdn_cache_refresh',
              'cdn_monitor_report',
              'cdn_log_manager',)

    # check host name
    def checkHost(self,request):
        host = request.get_host()
        host_list=host.split(':')
        host = host_list[0]
        currentHost = ''
        hostmanage = settings.HOSTMANAGE
        if hostmanage.has_key(host):
            currentHost = hostmanage[host]
        return currentHost


    def hideCdn(self, context):
        request = context['request']
        hostmanage = self.checkHost(request)
        if hostmanage:
            enable_cdn = hostmanage['enable_cdn']
            if not enable_cdn:
                self.nav = False


    def allowed(self, context):
        """Checks for role based access for this dashboard.

        Checks for access to any panels in the dashboard and of the the
        dashboard itself.

        This method should be overridden to return the result of
        any policy checks required for the user to access this dashboard
        when more complex checks are required.
        """

        # if the dashboard has policy rules, honor those above individual
        # panels
        self.hideCdn(context)
        if not self._can_access(context['request']):
            return False

        # check if access is allowed to a single panel,
        # the default for each panel is True
        for panel in self.get_panels():
            if panel.can_access(context):
                return True

        return False

horizon.register(Cdn)