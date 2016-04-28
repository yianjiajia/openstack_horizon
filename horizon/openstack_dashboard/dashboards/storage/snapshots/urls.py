#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from django.conf.urls import include
from django.conf.urls import patterns
from django.conf.urls import url

from openstack_dashboard.dashboards.storage.snapshots import views
from openstack_dashboard.dashboards.storage.snapshots.strategies import urls as strategy_urls

urlpatterns = patterns(
    '',
    url(r'^$', views.IndexView.as_view(), name='index'),
    url(r'^\?tab=snapshot_strategy_tabs__snapshots_tab$',
        views.IndexView.as_view(), name='snapshots_tab'),
    url(r'^\?tab=snapshot_strategy_tabs__strategies_tab$',
        views.IndexView.as_view(), name='strategies_tab'),
    url(r'^(?P<snapshot_id>[^/]+)$',
        views.DetailView.as_view(),
        name='detail'),
    url(r'^(?P<snapshot_id>[^/]+)/update/$',
        views.UpdateView.as_view(),
        name='update'),
    url(r'strategies/', include(strategy_urls, namespace='strategies')),
)
