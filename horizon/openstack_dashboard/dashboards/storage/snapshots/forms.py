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


from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import forms
from horizon import messages

from openstack_dashboard import api


class UpdateForm(forms.SelfHandlingForm):
    name = forms.CharField(max_length=50, label=_("Snapshot Name"))
    description = forms.CharField(max_length=255,
                                  widget=forms.Textarea(attrs={'rows': 4}),
                                  label=_("Description"),
                                  required=False)

    def handle(self, request, data):
        snapshot_id = self.initial['snapshot_id']
        try:
            api.cinder.volume_snapshot_update(request,
                                          snapshot_id,
                                          data['name'],
                                          data['description'])

            message = _('Updating volume snapshot "%s"') % data['name']
            messages.info(request, message)

            # operation log
            config = '\n'.join(['Snap ID: '+ snapshot_id, 'Snap Name: ' + data['name']])
            api.logger.Logger(request).create(resource_type='snapshot', action_name='Update Snapshot',
                                                       resource_name='Snapshot', config=config,
                                                       status='Success')
            return True
        except Exception:
            redirect = reverse("horizon:storage:volumes:index")
            exceptions.handle(request,
                              _('Unable to update volume snapshot.'),
                              redirect=redirect)

            # operation log
            api.logger.Logger(request).create(resource_type='snapshot', action_name='Update Snapshot',
                                                       resource_name='Snapshot', config='Unable to update volume snapshot',
                                                       status='Error')