from django.conf.urls import patterns
from django.conf.urls import url
from .views import IndexView, ajax_view


urlpatterns = patterns('',
    url(r'^$', IndexView.as_view(), name='index'),
    url(r'^\?tab=monitor_report__data_statistics$', IndexView.as_view(), name='data_statistics_tab'),
    url(r'^json$', ajax_view, kwargs={'tenant_id': '', 'domain_id': ''}),

)
