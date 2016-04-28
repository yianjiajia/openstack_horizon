from django.utils.translation import ugettext_lazy as _
from horizon import tabs
from openstack_dashboard.dashboards.project.cdn.cdn_cache_refresh \
    import tabs as project_tabs
from horizon import exceptions
from openstack_dashboard.dashboards.project.cdn.cdn_cache_refresh import constants
from horizon import messages
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse_lazy
from openstack_dashboard.dashboards.project.cdn import middware

INDEX = reverse_lazy('horizon:cdn:cdn.cdn_cache_refresh:index')


class IndexView(tabs.TabbedTableView):
    tab_group_class = project_tabs.CacheRefreshTabs
    template_name = constants.INFO_TEMPLATE_NAME
    page_title = _("Cache Fresh")

    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)
        try:
            pass
        except Exception:
            exceptions.handle(self.request,
                              _('Unable to get cache rule information.'))

        return context


def url_fresh(request):
    try:
        url_list = request.GET.get('url_list')
        url_purge_list = middware.purgeApi.PurgeBatch(urls=url_list.split('\n'))
        purge = middware.PurgeManage()
        ret = purge.purge(url_purge_list)
        if ret.getMsg() == "success":
            messages.success(request, ret.getMsg())
        else:
            messages.error(request, ret.getMsg())
    except Exception:
        exceptions.handle(request)
    return HttpResponseRedirect(INDEX)


def dir_fresh(request):
    try:
        dir_list = request.GET.get('dir_list')
        dir_purge_list = middware.purgeApi.PurgeBatch(dirs=dir_list.split('\n'))
        purge = middware.PurgeManage()
        ret = purge.purge(dir_purge_list)
        if ret.getMsg() == "success":
            messages.success(request, ret.getMsg())
        else:
            messages.error(request, ret.getMsg())
    except Exception:
        exceptions.handle(request)
    return HttpResponseRedirect(INDEX)




