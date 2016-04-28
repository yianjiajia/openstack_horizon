__author__ = 'yamin'
from django.conf.urls import patterns
from django.conf.urls import url
from openstack_dashboard.dashboards.settings.workorder import views
urlpatterns = patterns(
    '',
    url(r'^$', views.IndexView.as_view(), name='index'),
    url(r'^create$', views.CreateWorkOrder.as_view(), name='create'),
    url(r'^(?P<workorderno>.+)$', views.DetailView.as_view(), name='detail'),
)

