# Copyright 2012 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
#
# Copyright 2012 NEC Corporation
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

import logging

from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import forms
from horizon import messages

from openstack_dashboard import api


LOG = logging.getLogger(__name__)


class UpdateNetwork(forms.SelfHandlingForm):
    name = forms.CharField(label=_("Name"), required=False)
    tenant_id = forms.CharField(widget=forms.HiddenInput)
    network_id = forms.CharField(label=_("ID"),
                                 widget=forms.TextInput(
                                     attrs={'readonly': 'readonly'}))
    admin_state = forms.ChoiceField(choices=[(True, _('UP')),
                                             (False, _('DOWN'))],
                                    label=_("Admin State"))
    failure_url = 'horizon:network:networks:index'

    def handle(self, request, data):
        try:
            params = {'admin_state_up': (data['admin_state'] == 'True'),
                      'name': data['name']}
            network = api.neutron.network_update(request,
                                                 data['network_id'],
                                                 **params)
            msg = _('Network %s was successfully updated.') % data['name']
            LOG.debug(msg)
            messages.success(request, msg)

            # operation log
            config = _("Network ID: %s Network Name: %s") %(data['network_id'], data['name'])
            api.logger.Logger(request).create(resource_type='network', action_name='Update Network',
                                                       resource_name='Network', config=config,
                                                       status='Success')

            return network
        except Exception:
            msg = _('Failed to update network %s') % data['name']
            LOG.info(msg)
            redirect = reverse(self.failure_url)
            exceptions.handle(request, msg, redirect=redirect)

            api.logger.Logger(request).create(resource_type='network', action_name='Update Network',
                                                       resource_name='Network', config=_('Failed to update network %s') % data['name'],
                                                       status='Error')
