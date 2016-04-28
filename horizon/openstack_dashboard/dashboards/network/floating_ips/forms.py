# Copyright 2012 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
#
# Copyright 2012 Nebula, Inc.
# Copyright (c) 2012 X.commerce, a business unit of eBay Inc.
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

from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import forms
from horizon import messages

from openstack_dashboard import api
from openstack_dashboard.usage import quotas


class FloatingIpAllocate(forms.SelfHandlingForm):
    pool = forms.ChoiceField(label=_("Pool"))
    limit_speed = forms.IntegerField(label=_("Limit Speed(Mbps)"),
                                     min_value=-1,
                                     initial=-1,
                                     help_text=_("Should little than Total Bandwidth, Set -1 or 0 If want have no limit."))

    def __init__(self, *args, **kwargs):
        super(FloatingIpAllocate, self).__init__(*args, **kwargs)
        floating_pool_list = kwargs.get('initial', {}).get('pool_list', [])
        self.fields['pool'].choices = floating_pool_list

    def handle(self, request, data):
        try:
            # Prevent allocating more IP than the quota allows
            usages = quotas.tenant_quota_usages(request)
            if usages['floating_ips']['available'] <= 0:
                error_message = _('You are already using all of your available'
                                  ' floating IPs.')
                self.api_error(error_message)
                return False

            fip = api.network.tenant_floating_ip_allocate(request,
                                                          pool=data['pool'],
                                                          limit_speed=data['limit_speed'])
            messages.success(request,
                             _('Allocated Floating IP %(ip)s.')
                             % {"ip": fip.ip})


            # operation log
            config = _('Floating IP: %s') %fip.ip

            api.logger.Logger(request).create(resource_type='floatip', action_name='Allocated Floating IP',
                                                       resource_name='Floating IP', config=config,
                                                       status='Success')

            return fip
        except Exception:
            exceptions.handle(request, _('Unable to allocate Floating IP.'))

            # operation log
            api.logger.Logger(request).create(resource_type='floatip', action_name='Allocated Floating IP',
                                                       resource_name='Floating IP', config=_('Unable to allocate Floating IP.'),
                                                       status='Error')

class FloatingIpUpdate(forms.SelfHandlingForm):
    floating_ip_id = forms.CharField(widget=forms.HiddenInput())
    floating_ip_address = forms.CharField(
        label=_("Floating IP"),
        required=False,
        widget=forms.TextInput(attrs={'readonly': 'readonly'}),
    )
    limit_speed = forms.IntegerField(label=_("Limit Speed(Mbps)"),
                                     min_value=-1,
                                     initial=-1,
                                     help_text=_("Should little than Total Bandwidth, Set -1 or 0 If want have no limit."))
    
    def __init__(self, *args, **kwargs):
        super(FloatingIpUpdate, self).__init__(*args, **kwargs)
        self.is_fixed_ip_address = kwargs.get('initial', {}).get('is_fixed_ip_address', False)
        self.fixed_ip_address = kwargs.get('initial', {}).get('fixed_ip_address', None)
        self.port_id = kwargs.get('initial', {}).get('port_id', None)

    def handle(self, request, data):
        try:
            floating_ip_id = data['floating_ip_id']
            limit_speed = data['limit_speed']
            
            if self.is_fixed_ip_address:
                api.network.floating_ip_disassociate(request, floating_ip_id)
            
            fip = api.network.tenant_floating_ip_update(request, floating_ip_id, limit_speed)
            
            if self.is_fixed_ip_address:
                port_id = "%s_%s" % (self.port_id, self.fixed_ip_address)
                api.network.floating_ip_associate(request, floating_ip_id, port_id)
            
            messages.success(request,
                             _('Update Floating IP %(ip)s.')
                             % {"ip": fip.ip})

            # operation log
            config = _('Floating IP ID: %s') %floating_ip_id

            api.logger.Logger(request).create(resource_type='floatip', action_name='Update Floating IP',
                                                       resource_name='Floating IP', config=config,
                                                       status='Success')
            return True
        except Exception:
            exceptions.handle(request, _('Unable to update Floating IP.'))

            # operation log
            api.logger.Logger(request).create(resource_type='floatip', action_name='Update Floating IP',
                                                       resource_name='Floating IP', config= _('Unable to update Floating IP.'),
                                                       status='Error')

