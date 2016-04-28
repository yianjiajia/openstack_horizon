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

from openstack_dashboard.dashboards.identity.account import views

USER = r'^(?P<user_id>[^/]+)/%s$'

urlpatterns = patterns(
    'horizon.dashboards.identity.account.views',
    url(r'^$', views.IndexView.as_view(), name='index'),
    url(r'^create/$', views.CreateView.as_view(), name='create'),
    url(USER % 'update_info', views.UpdateInfoView.as_view(), name='update_info'),
    url(USER % 'detail', views.DetailView.as_view(), name='detail'),
    url(USER % 'update_quota', views.UpdateQuotaView.as_view(), name='update_quota'),
    url(USER % 'regions', views.UpdateRegionsView.as_view(), name='regions'),
    url(USER % 'update_member', views.UpdateMemberView.as_view(), name='update_member'),
    url(USER % 'change_password', views.ChangePasswordView.as_view(), name='change_password'))
