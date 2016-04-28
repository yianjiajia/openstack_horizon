# -*- coding: utf-8 -*-
'''
Created on 2015-06-05

@author: yanjj@syscloud.cn
'''

from django.utils.translation import ugettext_lazy as _
from horizon import tabs
from openstack_dashboard.dashboards.cdn.cdn_cache_refresh \
    import tabs as project_tabs
from horizon import exceptions
from openstack_dashboard.dashboards.cdn.cdn_cache_refresh import constants
from horizon import messages
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse_lazy
from openstack_dashboard.dashboards.cdn import middware
from openstack_dashboard.api.logger import Logger

INDEX = reverse_lazy('horizon:cdn:cdn_cache_refresh:index')


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
        if not url_list:
            return HttpResponseRedirect(INDEX)
        url_purge_list = middware.purgeApi.PurgeBatch(urls=url_list.split('\n'))
        purge = middware.PurgeManage()
        ret = purge.purge(url_purge_list)
        if ret.getMsg() == "success":
            messages.success(request, _("Success"))

            # 插入操作日志
            Logger(request).create(resource_type='CDN', action_name='Url Fresh',
                                   resource_name='CDN', config='', status='Success')
        else:
            messages.error(request, _("Bad Request:wrong domains"))
            # 插入操作日志
            Logger(request).create(resource_type='CDN', action_name='Url Fresh', resource_name='CDN', config='',
                                                       status='Error')
    except Exception:
         # 插入操作日志
        Logger(request).create(resource_type='CDN', action_name='Url Fresh', resource_name='CDN', config='',
                                                       status='Error')
        exceptions.handle(request)
    return HttpResponseRedirect(INDEX)


def dir_fresh(request):
    try:
        dir_list = request.GET.get('dir_list')
        if not dir_list:
            return HttpResponseRedirect(INDEX)
        dir_purge_list = middware.purgeApi.PurgeBatch(dirs=dir_list.split('\n'))
        purge = middware.PurgeManage()
        ret = purge.purge(dir_purge_list)
        if ret.getMsg() == "success":
            messages.success(request, _("Success"))

            # 插入操作日志
            Logger(request).create(resource_type='CDN', action_name='Dir Fresh',
                                   resource_name='CDN', config='', status='Success')
        else:
            messages.error(request, _("Bad Request:wrong domains"))

            # 插入操作日志
            Logger(request).create(resource_type='CDN', action_name='Dir Fresh',
                                   resource_name='CDN', config='', status='Error')
    except Exception:

        # 插入操作日志
        Logger(request).create(resource_type='CDN', action_name='Dir Fresh',
                                   resource_name='CDN', config='', status='Error')
        exceptions.handle(request)
    return HttpResponseRedirect(INDEX)




