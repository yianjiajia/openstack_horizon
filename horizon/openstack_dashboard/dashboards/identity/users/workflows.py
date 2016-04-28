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


from django.utils.translation import ugettext_lazy as _

import traceback
import logging

from django.conf import settings

from horizon import exceptions
from horizon import forms
from horizon import workflows

from openstack_dashboard import api
from openstack_dashboard.usage import quotas

LOG = logging.getLogger(__name__)

class UpdateRegionsAction(workflows.MembershipAction):
    # add user_id
    user_id = forms.CharField(widget=forms.HiddenInput, required=False)

    def __init__(self, request, *args, **kwargs):
        super(UpdateRegionsAction, self).__init__(request,
                                                       *args,
                                                       **kwargs)
        err_msg = _('Unable to retrieve region list. '
                    'Please try again later.')
        context = args[0]

        default_role_name = self.get_default_role_field_name()
        self.fields[default_role_name] = forms.CharField(required=False)
        self.fields[default_role_name].initial = 'member'

        # Get list of available regions.
        try:
            all_regions_obj = api.keystone.list_regions(request)
        except Exception:
            exceptions.handle(request, err_msg)
        all_regions = [(region_obj.id, region_obj.description)
                         for region_obj in all_regions_obj]
        # Get list of user related region
        user_id = context.get('user_id')
        try:
            if user_id:
                user_regions_db = api.keystone.list_regions_for_user(request, user_id)
                user_regions = [region['id'] for region in user_regions_db]
        except Exception:
            exceptions.handle(request, err_msg)

        field_name = self.get_member_field_name('member')
        self.fields[field_name] = forms.MultipleChoiceField(required=False)
        self.fields[field_name].choices = all_regions
        self.fields[field_name].initial = user_regions


    def clean(self):
        data = super(UpdateRegionsAction, self).clean()
        if len(data['update_regions_role_member']) < 1:
            msg = (_('User must be in one Region'))
            raise forms.ValidationError(msg)

        # if remove user from region in which user have resource, prevent it
        user = api.keystone.user_get(self.request, data['user_id'])
        user_id = user.id
        user_regions_db = api.keystone.list_regions_for_user(self.request, user_id)
        urs = set([region['id'] for region in user_regions_db])
        field_name = self.get_member_field_name('member')
        user_regions = data[field_name]
        form_regions = set(user_regions)
        to_remove = urs - form_regions
        for r in to_remove:
            usage = quotas.tenant_quota_usages(
                self.request, tenant_id=user.default_project_id, region=r)
            # only check fee resource
            fee_items = ['volumes', 'volume_gigabytes', 'snapshot_gigabytes', 'routers', 'ram', 'snapshots', 'instances', 'subnets',
                         'networks', 'floating_ips', 'pool', 'cores']
            for i in usage.usages:
                if i in fee_items:
                    if 'used' in usage[i] and usage[i]['used'] > 0:
                        msg = (_('User Have resource %s in region %s') % (i, r))
                        raise forms.ValidationError(msg)
        return data

    def set_region_quota(self, request, to_add, project_id):
        for r in to_add:
            try:
                api.nova.tenant_quota_update(request,
                                             project_id,
                                             region=r,
                                             **settings.QUOTA_DEFAULI['nova'])
                api.cinder.tenant_quota_update(request,
                                               project_id,
                                               region=r,
                                               **settings.QUOTA_DEFAULI['cinder'])
                api.neutron.tenant_quota_update(request,
                                                project_id,
                                                region=r,
                                                **settings.QUOTA_DEFAULI['neutron'])
            except Exception:
                LOG.error(traceback.format_exc())
                raise

    def handle(self, request, data):
        field_name = self.get_member_field_name('member')
        user_regions = data[field_name]
        user_id = data['user_id']

        user = api.keystone.user_get(request, user_id)
        user_regions_db = api.keystone.list_regions_for_user(request, user_id)
        urs = set([region['id'] for region in user_regions_db])
        form_regions = set(user_regions)
        to_add = form_regions - urs
        try:
            api.keystone.add_region_to_user(request, user_id, user_regions)
            if to_add:
                self.set_region_quota(request, to_add, user.default_project_id)
                
            # operation log
            config = _('Add user region: [%s]') % ','.join(to_add)
            api.logger.Logger(request).create(resource_type='account', action_name='Update Regions',
                                              resource_name='Account', config=config,
                                              status='Success')

        except Exception:
            # operation log
            config = _('Add user region: [%s]') % ','.join(to_add)
            api.logger.Logger(request).create(resource_type='account', action_name='Update Regions',
                                              resource_name='Account', config=config,
                                              status='Error')
            LOG.error(traceback.format_exc())
            exceptions.handle(request, _('can not update regions'))
        return True

    class Meta:
        name = _("Regions")
        slug = "update_regions"


class UpdateRegionsStep(workflows.UpdateMembersStep):
    action_class = UpdateRegionsAction
    help_text = _("Select available regions for current user.")
    available_list_title = _("All Regions")
    members_list_title = _("Selected Regions")
    no_available_text = _("No regions found.")
    no_members_text = _("No regions selected.")
    show_roles = False
    depends_on = ("user_id",)
    template_name = "identity/users/_workflow_step_update_regions.html"

    def contribute(self, data, context):
        if data:
            member_field_name = self.get_member_field_name('member')
            context[member_field_name] = data.get(member_field_name, [])
        return context


class UpdateRegions(workflows.Workflow):
    slug = "update_regions"
    name = _("Update Regions")
    #finalize_button_name = _("Update Regions")
    success_message = _('Updated regions.')
    failure_message = _('Unable to update regions.')
    success_url = "horizon:identity:users:index"
    default_steps = (UpdateRegionsStep,)

    def format_status_message(self, message):
        return message

