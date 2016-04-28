from django.conf.urls import patterns
from django.conf.urls import url
from .views import IndexView, ajax_view


urlpatterns = patterns('',
    url(r'^$', IndexView.as_view(), name='index'),
    url(r'^json$', ajax_view),

)
