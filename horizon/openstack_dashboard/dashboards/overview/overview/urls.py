# Copyright 2012 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
#
# Copyright 2012 Nebula, Inc.
#
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


from django.conf.urls import patterns
from django.conf.urls import url

from openstack_dashboard.dashboards.overview.overview import views

urlpatterns = patterns(
    'dashboards.overview.overview.views',
    url(r'^$', views.ProjectOverview.as_view(), name='index'),
    url(r'^warning$', views.WarningView.as_view(), name='warning'),
    url(r'^initnet/$', views.InitNetView.as_view(), name='initnet'),
    url(r'^initvpn/$', views.InitVPNView.as_view(), name='initvpn'),
    url(r'^initfirewall/$', views.InitFirewallView.as_view(), name='initfirewall'),
    url(r'^destroy/$', views.DestroyView.as_view(), name='destroy'),
)
