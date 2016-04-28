# Copyright 2013, Mirantis Inc
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
from openstack_dashboard.dashboards.member import views
urlpatterns = patterns('',
    #register port
    #by ying.zhou 
    url(r'checkUser/', views.ajaxCheckUser, name='home'),
    url(r'checkproject/', views.ajaxCheckProject, name='home'),
    url(r'updateUser/', views.ajaxUpdatePassword, name='home'),  
    url(r'sendEmail/', views.sendEmail, name='home'),
    url(r'updateUser/', views.updateUser, name='home'),
    url(r'createCode/', views.createCode, name='home'),
    url(r'checkCode/', views.checkCode, name='home'),
    url(r'sendMsg/', views.sendMsg, name='home'),
    url(r'checkMsg/', views.checkMsg, name='home'),

    
)
