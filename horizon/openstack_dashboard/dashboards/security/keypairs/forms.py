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

import re

from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import forms
from horizon import messages

from openstack_dashboard import api


NEW_LINES = re.compile(r"\r|\n")

KEYPAIR_NAME_REGEX = re.compile(r"^[\w\- ]+$", re.UNICODE)
KEYPAIR_ERROR_MESSAGES = {
    'invalid': _('Key pair name may only contain letters, '
                 'numbers, underscores, spaces and hyphens.')}


class CreateKeypair(forms.SelfHandlingForm):
    name = forms.RegexField(max_length=255,
                            label=_("Key Pair Name"),
                            regex=KEYPAIR_NAME_REGEX,
                            error_messages=KEYPAIR_ERROR_MESSAGES)

    def clean(self):
        cleaned_data = super(CreateKeypair, self).clean()
        name = cleaned_data.get('name')
        keypairs = api.nova.keypair_list(self.request)
        already_created = [k for k in keypairs if k.name == name]
        if already_created:
            msg = _('Keypair with the name %s have already created, please use a different name.') % (name)
            self._errors['name'] = self.error_class([msg])

            # operation log
            config = _('%s have already created') % name
            api.logger.Logger(self.request).create(resource_type='keypair', action_name='Create Keypair',
                                                       resource_name='Keypair', config=config,
                                                       status='Error')
        return self.cleaned_data

    def handle(self, request, data):

        # operation log
        config = _('Keypair Name: %s') %data['name']
        api.logger.Logger(request).create(resource_type='keypair', action_name='Create Keypair',
                                                       resource_name='Keypair', config=config,
                                                       status='Success')
        return True  # We just redirect to the download view.


class ImportKeypair(forms.SelfHandlingForm):
    name = forms.RegexField(max_length=255,
                            label=_("Key Pair Name"),
                            regex=KEYPAIR_NAME_REGEX,
                            error_messages=KEYPAIR_ERROR_MESSAGES)
    public_key = forms.CharField(label=_("Public Key"), widget=forms.Textarea(
        attrs={'class': 'modal-body-fixed-width'}))

    def clean(self):
        cleaned_data = super(ImportKeypair, self).clean()
        name = cleaned_data.get('name')
        keypairs = api.nova.keypair_list(self.request)
        already_created = [k for k in keypairs if k.name == name]
        if already_created:
            msg = _('Keypair with the name %s have already created, please use a different name.') % (name)
            self._errors['name'] = self.error_class([msg])

            # operation log
            config = _('%s have already created') % name
            api.logger.Logger(self.request).create(resource_type='keypair', action_name='Create Keypair',
                                                       resource_name='Keypair', config=config,
                                                       status='Error')
        return self.cleaned_data

    def handle(self, request, data):
        try:
            # Remove any new lines in the public key
            data['public_key'] = NEW_LINES.sub("", data['public_key'])
            keypair = api.nova.keypair_import(request,
                                              data['name'],
                                              data['public_key'])
            messages.success(request,
                             _('Successfully imported public key: %s')
                             % data['name'])

            # operation log
            config = _('Keypair Name: %s') %data['name']
            api.logger.Logger(self.request).create(resource_type='keypair', action_name='Import Keypair',
                                                       resource_name='Keypair', config=config,
                                                       status='Success')
            return keypair
        except Exception:
            exceptions.handle(request, ignore=True)
            self.api_error(_('Unable to import key pair.'))

            # operation log
            api.logger.Logger(self.request).create(resource_type='keypair', action_name='Import Keypair',
                                                       resource_name='Keypair', config='',
                                                       status='Error')
            return False