from django.conf.urls import patterns
from django.conf.urls import url
from openstack_dashboard.dashboards.cdn.cdn_cache_refresh import views

urlpatterns = patterns('',
                       url(r'^$', views.IndexView.as_view(), name='index'),
                       url(r'^\?tab=cache_refresh__refresh_schedule$', views.IndexView.as_view(),
                           name='refresh_schedule_tab'),
                       url(r'^url/$', views.url_fresh, name='urlfresh'),
                       url(r'^dir/$', views.dir_fresh, name='dirfresh'),
                       )
