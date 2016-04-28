from django.conf.urls import patterns
from django.conf.urls import url
from openstack_dashboard.dashboards.cdn.cdn_domain_manager import views
DOMAIN_URL = r'^(?P<domain_id>[^/]+)/%s'

urlpatterns = patterns('',
    url(r'^$', views.IndexView.as_view(), name='index'),
    url(r'^create/$', views.CreateView.as_view(), name='create'),
    url(DOMAIN_URL % 'update',
        views.UpdateTabView.as_view(), name='update'),
    url(DOMAIN_URL % 'verify',
        views.VerifyView.as_view(), name='verify'),
    url(DOMAIN_URL % 'addaccess',
        views.AddAccessFormView.as_view(), name='addaccess'),
    url(r'^(?P<domain_id>[^/]+)/modifyaccess/(?P<access_id>[^/]+)/update$',
        views.ModifyAccessFormView.as_view(), name='modifyaccess'),
    url(DOMAIN_URL % 'addcache',
        views.AddCacheFormView.as_view(), name='addcache'),
    url(r'^(?P<domain_id>[^/]+)/modifycache/(?P<cache_id>[^/]+)/update$',
        views.ModifyCacheFormView.as_view(), name='modifycache'),
    url(DOMAIN_URL % 'modify',
        views.UpdateDomainFormView.as_view(), name='modify'),
    url(DOMAIN_URL % 'action',
        views.verify_view, name='action'),
    url(r'^modifyaccountmode/$', views.ModifyAccountMode.as_view(), name="modifyaccountmode")
    )



