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
from openstack_dashboard.dashboards.admin.cdn import views
from  openstack_dashboard.dashboards.cdn.cdn_monitor_report.views import ajax_view

TENANT = r'^(?P<tenant_id>[^/]+)/$'
DOMAIN = r'^(?P<tenant_id>[^/]+)/(?P<domain_id>[^/]+)/$'
urlpatterns = patterns(
    '',
    url(r'^$', views.AllDomainDetail.as_view(), name='index'),
    url(DOMAIN, views.DomainDetailView.as_view(), name='domain_detail'),
    url(TENANT, views.TenantDetailView.as_view(), name='tenant_detail'),
    url(r'^(?P<tenant_id>[^/]+)/(?P<domain_id>[^/]+)/json$', ajax_view),
    url(r'^(?P<tenant_id>[^/]+)/json$', ajax_view, kwargs={'domain_id': ''}),
    )
