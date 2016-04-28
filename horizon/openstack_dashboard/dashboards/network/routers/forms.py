# Copyright 2012,  Nachi Ueno,  NTT MCL,  Inc.
# All rights reserved.

# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""
Views for managing Neutron Routers.
"""
import logging

from django.core.urlresolvers import reverse
from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext_lazy as _
from django.core.validators import MaxValueValidator
from django.conf import settings

from horizon import exceptions
from horizon import forms
from horizon import messages
import datetime

from openstack_dashboard import api

LOG = logging.getLogger(__name__)


class CreateForm(forms.SelfHandlingForm):
    name = forms.CharField(max_length=255, label=_("Router Name"))
    admin_state_up = forms.ChoiceField(label=_("Admin State"),
                                       choices=[(True, _('UP')),
                                                (False, _('DOWN'))],
                                       required=False)
    external_network = forms.ChoiceField(label=_("External Network"),
                                         required=True)
    bandwidth = forms.IntegerField(label=_('Bandwidth (Mbps)'),
                                  min_value=1, required=True)
    mode = forms.ChoiceField(label=_("Router Type"))
    ha = forms.ChoiceField(label=_("High Availability Mode"))
    failure_url = 'horizon:network:routers:index'

    def __init__(self, request, *args, **kwargs):
        super(CreateForm, self).__init__(request, *args, **kwargs)
        self.dvr_allowed = api.neutron.get_feature_permission(self.request,
                                                              "dvr", "create")
        if self.dvr_allowed:
            mode_choices = [('server_default', _('Use Server Default')),
                            ('centralized', _('Centralized')),
                            ('distributed', _('Distributed'))]
            self.fields['mode'].choices = mode_choices
        else:
            del self.fields['mode']

        self.ha_allowed = api.neutron.get_feature_permission(self.request,
                                                             "l3-ha", "create")
        if self.ha_allowed:
            ha_choices = [('server_default', _('Use Server Default')),
                          ('enabled', _('Enable HA mode')),
                          ('disabled', _('Disable HA mode'))]
            self.fields['ha'].choices = ha_choices
        else:
            del self.fields['ha']
        networks = self._get_network_list(request)
        if networks:
            self.fields['external_network'].choices = networks
        else:
            del self.fields['external_network']
        if not request.user.is_superuser:
            max_router_bandwidth_for_user = getattr(settings, 'MAX_ROUTER_BANDWIDTH_FOR_USER', 50)
            self.fields['bandwidth'].validators.append(MaxValueValidator(max_router_bandwidth_for_user))

    def _get_network_list(self, request):
        search_opts = {'router:external': True}
        try:
            networks = api.neutron.network_list(request, **search_opts)
        except Exception:
            msg = _('Failed to get network list.')
            LOG.info(msg)
            messages.warning(request, msg)
            networks = []

        choices = [(network.id, network.name or network.id)
                   for network in networks]
        if choices:
            choices.insert(0, ("", _("Select network")))
        return choices

    def handle(self, request, data):
        try:
            params = {'name': data['name']}
            params['bandwidth'] = data['bandwidth']
            if 'admin_state_up' in data and data['admin_state_up']:
                params['admin_state_up'] = data['admin_state_up']
            if 'external_network' in data and data['external_network']:
                params['external_gateway_info'] = {'network_id':
                                                   data['external_network']}
            if (self.dvr_allowed and data['mode'] != 'server_default'):
                params['distributed'] = (data['mode'] == 'distributed')
            if (self.ha_allowed and data['ha'] != 'server_default'):
                params['ha'] = (data['ha'] == 'enabled')
            router = api.neutron.router_create(request, **params)
            message = _('Router %s was successfully created.') % data['name']
            messages.success(request, message)

            # operation log
            config = _('Route Name: %s') %data['name']
            api.logger.Logger(request).create(resource_type='route', action_name='Create Route',
                                                       resource_name='Route', config=config,
                                                       status='Success')


            return router
        except Exception as exc:
            if exc.status_code == 409:
                msg = _('Quota exceeded for resource router.')
            else:
                msg = _('Failed to create router "%s".') % data['name']
            LOG.info(msg)
            redirect = reverse(self.failure_url)
            exceptions.handle(request, msg, redirect=redirect)

            # operation log
            api.logger.Logger(request).create(resource_type='route', action_name='Create Route',
                                                       resource_name='Route', config=msg,
                                                       status='Error')
            return False


class UpdateForm(forms.SelfHandlingForm):
    name = forms.CharField(label=_("Name"), required=False)
    admin_state = forms.ChoiceField(choices=[(True, _('UP')),
                                             (False, _('DOWN'))],
                                    label=_("Admin State"))
    router_id = forms.CharField(label=_("ID"),
                                widget=forms.TextInput(
                                    attrs={'readonly': 'readonly'}))
    bandwidth = forms.IntegerField(label=_('Bandwidth (Mbps)'),
                                  min_value=1, required=True)
    mode = forms.ChoiceField(label=_("Router Type"))
    ha = forms.BooleanField(label=_("High Availability Mode"), required=False)

    redirect_url = reverse_lazy('horizon:network:routers:index')

    def __init__(self, request, *args, **kwargs):
        super(UpdateForm, self).__init__(request, *args, **kwargs)
        self.dvr_allowed = api.neutron.get_feature_permission(self.request,
                                                              "dvr", "update")
        if not self.dvr_allowed:
            del self.fields['mode']
        elif kwargs.get('initial', {}).get('mode') == 'distributed':
            # Neutron supports only changing from centralized to
            # distributed now.
            mode_choices = [('distributed', _('Distributed'))]
            self.fields['mode'].widget = forms.TextInput(attrs={'readonly':
                                                                'readonly'})
            self.fields['mode'].choices = mode_choices
        else:
            mode_choices = [('centralized', _('Centralized')),
                            ('distributed', _('Distributed'))]
            self.fields['mode'].choices = mode_choices

        # TODO(amotoki): Due to Neutron Bug 1378525, Neutron disables
        # PUT operation. It will be fixed in Kilo cycle.
        # self.ha_allowed = api.neutron.get_feature_permission(
        #     self.request, "l3-ha", "update")
        self.ha_allowed = False
        if not self.ha_allowed:
            del self.fields['ha']
        if not request.user.is_superuser:
            max_router_bandwidth_for_user = getattr(settings, 'MAX_ROUTER_BANDWIDTH_FOR_USER', 50)
            self.fields['bandwidth'].validators.append(MaxValueValidator(max_router_bandwidth_for_user))
        updated_at=kwargs.get('initial')['updated_at']
        if updated_at:
            if (datetime.datetime.utcnow()-datetime.timedelta(hours=1))<=datetime.datetime.strptime(updated_at,'%Y-%m-%d %H:%M:%S'):
                self.fields['bandwidth'].widget = forms.TextInput(attrs={'readonly':
                                                                'readonly'})

    def handle(self, request, data):
        try:
            updated_at=self.initial['updated_at']
            if updated_at:
                if (datetime.datetime.utcnow()-datetime.timedelta(hours=1))<=datetime.datetime.strptime(updated_at,'%Y-%m-%d %H:%M:%S'):
                    if self.initial['bandwidth']!=data['bandwidth']:
                        msg = _('Failed to update router %s') % data['name']
                        LOG.info(msg)
                        exceptions.handle(request, msg, redirect=self.redirect_url)
            params = {'admin_state_up': (data['admin_state'] == 'True'),
                      'name': data['name'], 'bandwidth': data['bandwidth']}
            if self.dvr_allowed:
                params['distributed'] = (data['mode'] == 'distributed')
            if self.ha_allowed:
                params['ha'] = data['ha']
#            params['updated_at']=datetime.datetime.utcnow()
            router = api.neutron.router_update(request, data['router_id'],
                                               **params)
            msg = _('Router %s was successfully updated.') % data['name']
            LOG.debug(msg)
            messages.success(request, msg)

            # operation log
            config = _('Route ID: %s Route Name: %s up/off: %s  Bandwidth: %sMb/s') %(data['router_id'], data.get('name',''),
                                                                                  data['admin_state'], str(data['bandwidth']))

            api.logger.Logger(request).create(resource_type='route', action_name='Update Router',
                                                       resource_name='Route', config=config,
                                                       status='Success')
            return router
        except Exception:
            msg = _('Failed to update router %s') % data['name']
            LOG.info(msg)
            exceptions.handle(request, msg, redirect=self.redirect_url)

            api.logger.Logger(request).create(resource_type='route', action_name='Update Router',
                                                       resource_name='Route', config=msg,
                                                       status='Error')