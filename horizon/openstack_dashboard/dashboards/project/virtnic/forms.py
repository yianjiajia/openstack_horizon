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
from django.core.urlresolvers import reverse_lazy

from horizon import exceptions
from horizon import forms
from horizon import messages

from openstack_dashboard import api


LOG = logging.getLogger(__name__)


class CreateForm(forms.SelfHandlingForm):
    name = forms.CharField(max_length=255, label=_("Virtnic Name"))
    description = forms.CharField(widget=forms.Textarea(attrs={'rows': 4}), 
                                  required=False, label=_("Description"))
    subnetwork = forms.ChoiceField(label=_("Subnetwork"),
                                         required=True)
    failure_url = 'horizon:project:virtnic:index'

    def __init__(self, request, *args, **kwargs):
        super(CreateForm, self).__init__(request, *args, **kwargs)
        networks = self._get_network_list(request)
        if networks:
            self.fields['subnetwork'].choices = networks
        else:
            del self.fields['subnetwork']

    def _get_network_list(self, request):
        search_opts = {'router:external': False}
        try:
            tenant_id = self.request.user.tenant_id
            networks = api.neutron.network_list_for_tenant(request, tenant_id,**search_opts)
        except Exception:
            msg = _('Failed to get network list.')
            LOG.info(msg)
            messages.warning(request, msg)
            networks = []

        choices = [(network.id, network.name or network.id)
                   for network in networks]
#         if choices:
        choices.insert(0, ("", _("Select network")))
        return choices

    def handle(self, request, data):
        try:
            network_id=data['subnetwork']
            params = {'name': data['name'],'description':data["description"],"flag":"manual"}
            port = api.neutron.port_create(request, network_id,**params)
            message = _('Virtnic %s was successfully created.') % data['name']
            messages.success(request, message)
            return port
        except Exception as exc:
            if exc.status_code == 409:
                msg = _('Quota exceeded for resource Virtic.')
            else:
                msg = _('Failed to create virtic %s.') % data['name']
            LOG.info(msg)
            redirect = reverse(self.failure_url)
            exceptions.handle(request, msg, redirect=redirect)
            return False
    
    
class BindingForm(forms.SelfHandlingForm):
    name = forms.CharField(label=_("Name"), widget=forms.TextInput(
                                    attrs={'readonly': 'readonly'}))
    server = forms.ChoiceField(label=_("Server"),
                                         required=True)
    port_id = forms.CharField(label=_("ID"),
                                widget=forms.TextInput(
                                    attrs={'readonly': 'readonly'}))

    redirect_url = reverse_lazy('horizon:project:virtnic:index')

    def __init__(self, request, *args, **kwargs):
        super(BindingForm, self).__init__(request, *args, **kwargs)
        servers=self._get_server_list(request)
        if servers:
            self.fields['server'].choices = servers
        else:
            del self.fields['server']
    
    def _get_server_list(self, request):
#         search_opts = {'router:external': False}
        try:
            servers,has_more_data = api.nova.server_list(request)
        except Exception:
            msg = _('Failed to get server list.')
            LOG.info(msg)
            messages.warning(request, msg)
            servers = []
        choices = [(server.id, server.name or server.id)
                   for server in servers]
#         if choices:
        choices.insert(0, ("", _("Select server")))
        return choices

    def handle(self, request, data):
        try:
            instance_id=data["server"]
            port_id=data["port_id"]
            virtnic=api.nova.interface_attach(request, instance_id, port_id);
            msg = _('Virtnic %s was successfully bindinged.') % data['name']
            LOG.debug(msg)
            import time 
            time.sleep(3)
            messages.success(request, msg)
            return virtnic
        except Exception:
            msg = _('Failed to binding %s') % data['name']
            LOG.info(msg)
            exceptions.handle(request, msg, redirect=self.redirect_url)



