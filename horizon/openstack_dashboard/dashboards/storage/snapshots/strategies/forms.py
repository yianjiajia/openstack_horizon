# Copyright 2012 Nebula, Inc.
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
Views for managing volumes.
"""

#from oslo_utils import units

from django.conf import settings
from django.core.urlresolvers import reverse
#from django.forms import ValidationError  # noqa
#from django import http
#from django.template.defaultfilters import filesizeformat  # noqa
#from django.utils.translation import pgettext_lazy
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import forms
from horizon import messages
#from horizon.utils import functions
#from horizon.utils.memoized import memoized  # noqa
from openstack_dashboard import api
from openstack_dashboard.api import cinder

def _make_strategy_snapshot_at_choices(time_segment_length=None):
    if time_segment_length is None:
        time_segment_length = settings.AUTO_SNAPSHOT_TIME_SEGMENT_LENGTH
    return [(str(i + 1),'%02d:00-%02d:00' % (i % 24 + 1, (i + time_segment_length) % 24 + 1)) \
            for i in xrange(24) if i % time_segment_length == 0]

class UpdateForm(forms.SelfHandlingForm):
    name = forms.CharField(max_length=255, label=_("Strategy Name"))
    volume_id = forms.CharField(label=_("Select Volume"))
    snapshot_at =  forms.ChoiceField(label=_("Snapshot At"))
    max_keep_number = forms.IntegerField(label=_("Max Keep Snapshot Numbers"), min_value=0, initial=1)
    keep_last_sunday = forms.BooleanField(label=_("Keep Last Sunday or Not"), required=False)
    status = forms.BooleanField(label=_("Use or Not"), required=False)

    def __init__(self, request, *args, **kwargs):
        super(UpdateForm, self).__init__(request, *args, **kwargs)
        self.fields['snapshot_at'].choices = _make_strategy_snapshot_at_choices()
        self.fields["snapshot_at"].initial = self.initial['snapshot_at']

    def handle(self, request, data):
        strategy_id = self.initial['strategy_id']
        try:
            api.cinder.volume_snapshot_strategy_update(request,
                                                       strategy_id,
                                                       data['name'],
                                                       data['snapshot_at'],
                                                       data['keep_last_sunday'],
                                                       data['max_keep_number'],
                                                       data['status'])

            message = _('Updating volume snapshot strategy "%s"') % data['name']
            messages.success(request, message)

            # operation log
            config = _('Strategy ID: %s Strategy Name: %s') %(strategy_id, data['name'])
            api.logger.Logger(request).create(resource_type='strategy', action_name=_('Update Snapshot Strategy'),
                                                       resource_name=_('Snapshot Strategy'), config=config,
                                                       status='Success')
            return True
        except Exception:
            redirect = reverse("horizon:storage:snapshots:index")
            exceptions.handle(request,
                              _('Unable to update volume snapshot strategy.'),
                              redirect=redirect)

            # operation log
            api.logger.Logger(request).create(resource_type='strategy', action_name=_('Update Snapshot Strategy'),
                                                       resource_name=_('Snapshot Strategy'), config=_('Unable to update volume snapshot strategy'),
                                                       status='Error')

class CreateSnapshotStrategyForm(forms.SelfHandlingForm):
    name = forms.CharField(max_length=255, label=_("Strategy Name"))
    volume_id = forms.ChoiceField(label=_("Select Volume"))
    snapshot_at =  forms.ChoiceField(label=_("Snapshot At"))
    max_keep_number = forms.IntegerField(label=_("Max Keep Snapshot Numbers"), min_value=0, initial=1)
    keep_last_sunday = forms.BooleanField(label=_("Keep Last Sunday or Not"), required=False)
    status = forms.BooleanField(label=_("Use or Not"), required=False)

    def __init__(self, request, *args, **kwargs):
        super(CreateSnapshotStrategyForm, self).__init__(request, *args, **kwargs)

        # populate volume_id
        volumes = cinder.volume_list(request)
        choises = [(volume.id, volume.name) for volume in volumes]
        self.fields['volume_id'].choices = choises or [("", _("No volume"))]
        self.fields['snapshot_at'].choices = _make_strategy_snapshot_at_choices()

    def handle(self, request, data):
        try:
            snapshot_strategy = cinder.volume_snapshot_strategy_create(request,
                                                              data['volume_id'],
                                                              data['name'],
                                                              data['snapshot_at'],
                                                              data['keep_last_sunday'],
                                                              data['max_keep_number'],
                                                              data['status'])
            message = _('Creating volume snapshot strategy "%s".') % data['name']
            messages.info(request, message)

            # operation log
            config = _('Strategy ID: %s Strategy Name: %s') %(snapshot_strategy.id, data['name'])
            api.logger.Logger(request).create(resource_type='strategy', action_name='Create Snapshot Strategy',
                                                       resource_name='Strategy', config=config,
                                                       status='Success')

            return snapshot_strategy
        except Exception as e:
            redirect = reverse("horizon:storage:snapshots:strategies_tab")
            msg = _('Unable to create volume snapshot strategy.')
            code = getattr(e, 'code', None)
            if code is not None and code == 413:
                msg = _('Requested snapshot would exceed the allowed quota.')
            exceptions.handle(request,
                              msg,
                              redirect=redirect)

            # operation log
            api.logger.Logger(request).create(resource_type='strategy', action_name='Create Snapshot Strategy',
                                                       resource_name='Strategy', config=msg,
                                                       status='Error')
