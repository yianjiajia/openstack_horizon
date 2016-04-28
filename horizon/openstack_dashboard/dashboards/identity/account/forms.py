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

import json

from django.utils.translation import ugettext_lazy as _
from django import http
from django.conf import settings
from django.views.decorators.debug import sensitive_variables  # noqa
from django.core.validators import MaxValueValidator

from horizon import exceptions
from horizon import forms
from horizon import messages
from horizon.utils import functions as utils

from openstack_dashboard import api
from openstack_dashboard import policy
from openstack_dashboard.usage import quotas
from openstack_dashboard.dashboards.identity.account.workflows import NEUTRON_QUOTA_FIELDS
from openstack_dashboard.dashboards.identity.account.workflows import NOVA_QUOTA_FIELDS
from openstack_dashboard.dashboards.identity.users.forms import PasswordMixin


PROJECT_REQUIRED = api.keystone.VERSIONS.active < 3


class UpdateAccountInfoForm(forms.SelfHandlingForm):
    id = forms.CharField(label=_("ID"), widget=forms.HiddenInput, required=False)
    project_id = forms.CharField(label=_("Project ID"), widget=forms.HiddenInput, required=False)
    company = forms.CharField(label=_("Company"))
    email = forms.EmailField(
        label=_("Email"),
        required=True)
    telephone = forms.CharField(
        label=_("Telephone"),
        required=True)
    regionId = forms.ChoiceField(label=_("Primary Region"),
                                 required=PROJECT_REQUIRED)
    safeCard = forms.CharField(widget=forms.HiddenInput(),
                               required=False)

    def __init__(self, request, *args, **kwargs):
        super(UpdateAccountInfoForm, self).__init__(request, *args, **kwargs)
        region_choices = []
        user_id=kwargs['initial'].get('id', None)
        regions = api.keystone.list_regions_for_user(self.request, user_id)
        for region in regions:
            region_choices.append((region['id'], region['description']))
        region_choices.insert(0, ('', _("Select a region")))
        self.fields['regionId'].choices = region_choices

    def clean(self):
        cleaned_data = super(UpdateAccountInfoForm, self).clean()
        company = cleaned_data['company']
        user = api.keystone.user_list(self.request, filters={'company': company})
        if user and user[0].id != cleaned_data['id']:
            msg = (_('Company with name %s already exsit, please use another one.') %
                   company)
            raise forms.ValidationError(msg)
        return cleaned_data

    def _update_user(self, request, data):
        user = {}
        project = {}
        user_id = data['id']
        if "email" in data:
            user['email'] = data['email'] or None
        if "company" in data:
            user['company'] = data['company'] or None
            project['name'] = data['company'] or None
        if "telephone" in data:
            user['telephone'] = data['telephone'] or None
        if "regionId" in data:
            user['regionId'] = data['regionId'] or None

        try:
            response = api.keystone.user_update(request, user_id, **user)
        except Exception:
            response = exceptions.handle(request, ignore=True)
            messages.error(request, _('Unable to update the user.'))
        try:
            response = api.keystone.tenant_update(request, project=data['project_id'], name=data['company'])
        except Exception:
            response = exceptions.handle(request, ignore=True)
            messages.error(request, _('Unable to update project'))
        return response

    def handle(self, request, data):
        # set primary project for user
        user = self._update_user(request, data)
        if not user:
            # operation log
            config = _('Account name: %s') % data['company']
            api.logger.Logger(request).create(resource_type='account', action_name='Update Account',
                                              resource_name='Account', config=config,
                                              status='Error')
            return False

        # operation log
        config = _('Account name: %s') % data['company']
        api.logger.Logger(request).create(resource_type='account', action_name='Update Account',
                                          resource_name='Account', config=config,
                                          status='Success')
        messages.success(request,
                 _('User has been updated successfully.'))
        return True


class UpdateQuotaForm(forms.SelfHandlingForm):
    project_id = forms.CharField(label=_("Project ID"), widget=forms.HiddenInput, required=False)
    user_id = forms.CharField(label=_("User ID"), widget=forms.HiddenInput, required=False)

    # user_type = forms.ChoiceField(
    #     label=_("User Type"),
    #     required=True,
    #     choices=[('normal', _("Normal User")), ('credit', _("Credit User"))],
    #     widget=forms.Select(
    #         attrs={
    #             'class': 'switchable',
    #             'data-slug': 'user_type'
    #         }
    #     )
    # )
    #
    # credit_line = forms.FloatField(
    #     label=_("Credit Line"),
    #     required=False,
    #     min_value=0.0,
    #     widget=forms.TextInput(
    #         attrs={
    #             'class': 'switched',
    #             'data-switch-on': 'user_type',
    #             'data-user_type-credit': _('Credit'),
    #         }))
    # adjust_quota = forms.BooleanField(
    #     label=_("Adjust Quota"),
    #     required=False,
    #     widget=forms.CheckboxInput(
    #         attrs={
    #             'class': 'switchable',
    #             'data-slug': 'adjust_quota',
    #             'data-hide-on-checked': 'false'
    #         }
    #     )
    # )
    region_id = forms.ChoiceField(label=_("Regions"), required=True,
                                  widget=forms.SelectWidget(attrs={
                                       # 'class': 'switched',
                                       # 'data-switch-on': 'adjust_quota',
                                       # 'data-is-required': 'true',
                                       'style': 'width 10%'
                                   }))
    instances = forms.IntegerField(min_value=-1, label=_("Instances"),
                                   required=True,
                                   widget=forms.TextInput(attrs={
                                       # 'class': 'switched',
                                       # 'data-switch-on': 'adjust_quota',
                                       # 'data-is-required': 'true',
                                       'style': 'width 10%'
                                   }))

    cores = forms.IntegerField(min_value=2, label=_("VCPUs"),
                               required=True,
                               widget=forms.TextInput(attrs={
                                   # 'class': 'switched',
                                   # 'data-switch-on': 'adjust_quota',
                                   # 'data-is-required': 'true'
                               }))
    ram = forms.IntegerField(min_value=-1, label=_("RAM (MB)"),
                             required=True,
                             widget=forms.TextInput(attrs={
                                 # 'class': 'switched',
                                 # 'data-switch-on': 'adjust_quota',
                                 # 'data-is-required': 'true'
                             }))
    volumes = forms.IntegerField(min_value=-1, label=_("Volumes"),
                                 required=True,
                                 widget=forms.TextInput(attrs={
                                     # 'class': 'switched',
                                     # 'data-switch-on': 'adjust_quota',
                                     # 'data-is-required': 'true'
                                 }))
    snapshots = forms.IntegerField(min_value=-1, label=_("Volume Snapshots"),
                                   required=True,
                                   widget=forms.TextInput(attrs={
                                       # 'class': 'switched',
                                       # 'data-switch-on': 'adjust_quota',
                                       # 'data-is-required': 'true'
                                   }))
    volume_gigabytes = forms.IntegerField(
        min_value=-1, label=_("Size of Volumes(GB)"),
        required=True,
        widget=forms.TextInput(attrs={
            # 'class': 'switched',
            # 'data-switch-on': 'adjust_quota',
            # 'data-is-required': 'true'
        }))
    snapshot_gigabytes = forms.IntegerField(
        min_value=-1, label=_("Size of Snapshots (GB)"),
        required=True,
        widget=forms.TextInput(attrs={
            # 'class': 'switched',
            # 'data-switch-on': 'adjust_quota',
            # 'data-is-required': 'true'
        }))
    floatingip = forms.IntegerField(min_value=-1, label=_("Floating IPs"),
                                    required=True,
                                    widget=forms.TextInput(attrs={
                                        # 'class': 'switched',
                                        # 'data-switch-on': 'adjust_quota',
                                        # 'data-is-required': 'true'
                                    }))
    network = forms.IntegerField(min_value=-1, label=_("Networks"),
                                 required=True,
                                 widget=forms.TextInput(attrs={
                                     # 'class': 'switched',
                                     # 'data-switch-on': 'adjust_quota',
                                     # 'data-is-required': 'true'
                                 }))
    router = forms.IntegerField(min_value=-1, label=_("Routers"),
                                required=True,
                                widget=forms.TextInput(attrs={
                                    # 'class': 'switched',
                                    # 'data-switch-on': 'adjust_quota',
                                    # 'data-is-required': 'true'
                                }))
    subnet = forms.IntegerField(min_value=-1, label=_("Subnets"),
                                required=True,
                                widget=forms.TextInput(attrs={
                                    # 'class': 'switched',
                                    # 'data-switch-on': 'adjust_quota',
                                    # 'data-is-required': 'true'
                                }))
    pool = forms.IntegerField(min_value=-1, label=_("Loadbalancers"),
                              required=True,
                              widget=forms.TextInput(attrs={
                                  # 'class': 'switched',
                                  # 'data-switch-on': 'adjust_quota',
                                  # 'data-is-required': 'true'
                              }))
    bandwidth = forms.IntegerField(required=False, widget=forms.HiddenInput)

    def __init__(self, request, *args, **kwargs):
        super(UpdateQuotaForm, self).__init__(request, *args, **kwargs)
        region_choices = []
        user_id = kwargs['initial'].get('user_id', None)
        regions = api.keystone.list_regions_for_user(self.request, user_id)
        for region in regions:
            region_choices.append((region['id'], region['description']))
        self.fields['region_id'].choices = region_choices
        # if kwargs['initial']['user_type'] == 'credit':
        #     self.fields['user_type'].choices = [('credit', _("Credit User"))]
        #
        # if policy.check((("identity", "project_admin_required"),), self.request):
        #     self.fields['credit_line'].validators.append(MaxValueValidator(settings.UPPER_CREDIT_LINE_FOR_PROJECT_ADMIN))
        #     self.fields['credit_line'].help_text = _('credit line is between 0~%s') % settings.UPPER_CREDIT_LINE_FOR_PROJECT_ADMIN


    def clean(self):
        cleaned_data = super(UpdateQuotaForm, self).clean()
        usages = quotas.tenant_quota_usages(
            self.request, tenant_id=self.initial['project_id'], region=cleaned_data['region_id'])
        # Validate the quota values before updating quotas.
        # add key based on cleaned data, do not update tenant_quota_usages because
        # do not know if hava affect on others
        need_trans = {'network': 'networks', 'subnet': 'subnets', 'router': 'routers', 'floatingip': 'floating_ips'}
        bad_values = []
        for key, value in cleaned_data.items():
            if key in need_trans:
                key = need_trans[key]
            used = usages[key].get('used', 0)
            if value is not None and value >= 0 and used > value:
                bad_values.append(_('%(used)s %(key)s used') %
                                  {'used': used,
                                   'key': quotas.QUOTA_NAMES.get(key, key)})
        if bad_values:
            value_str = ", ".join(bad_values)
            msg = (_('Quota value(s) cannot be less than the current usage '
                     'value(s): %s.') %
                   value_str)
            raise forms.ValidationError(msg)
        return cleaned_data

    # def _update_billing_accout(self, request, project_id, data):
    #     client = api.billing.RequestClient(request)
    #     account = client.get_account(project_id)
    #     if data['user_type'] == 'credit' and account['type'] != 'credit':
    #         ret = client.api_request('/account/change2credit/' + account['account_id'] + '?credit_line=' + str(data['credit_line']), method='GET')
    #         user = json.loads(ret.read())
    #         if user['success'] != 'success':
    #             raise
    #         return True
    #     else:
    #         # change credit line
    #         if data['user_type'] == 'credit':
    #             ret = client.api_request(
    #                 '/account/changecreditline/' + account['account_id'] + '?credit_line=' + str(data['credit_line']),
    #                 method='GET')
    #             user = json.loads(ret.read())
    #             if user['success'] != 'success':
    #                 raise
    #         return True

    # def _update_user(self, request, data):
    #     try:
    #         response = self._update_billing_accout(request, data['project_id'], data)
    #     except Exception:
    #         response = exceptions.handle(request, ignore=True)
    #         messages.error(request, _('Unable to update user account.'))
    #
    #     if isinstance(response, http.HttpResponse):
    #         return response
    #     else:
    #         return response

    def _update_project_quota(self, request, data, project_id):
        # Update the project quota.
        nova_data = dict(
            [(key, data[key]) for key in NOVA_QUOTA_FIELDS])
        try:
            api.nova.tenant_quota_update(request, project_id, region=data['region_id'], **nova_data)

            if api.base.is_service_enabled(request, 'volume'):
                cinder_data = dict([(key, data[key]) for key in
                                    quotas.CINDER_QUOTA_FIELDS])
                api.cinder.tenant_quota_update(request,
                                           project_id,
                                           region=data['region_id'],
                                           **cinder_data)
            if api.base.is_service_enabled(request, 'network') and \
                    api.neutron.is_quotas_extension_supported(request):
                neutron_data = {}
                for key in NEUTRON_QUOTA_FIELDS:
                    neutron_data[key] = data[key]
                api.neutron.tenant_quota_update(request,
                                                project_id,
                                                region=data['region_id'],
                                                **neutron_data)
        except Exception:
            exceptions.handle(request, _('Unable to set project quotas.'))
            raise

    def handle(self, request, data):
        # set primary project for user
        try:
            # user = self._update_user(request, data)
            # if not user:
            #     raise
            project_id = data['project_id']
            self._update_project_quota(request, data, project_id)
            messages.success(request,
                     _('User has been updated successfully.'))
        except Exception:
             # operation log
            config = _('Project ID: %s') % data['project_id']
            api.logger.Logger(request).create(resource_type='account', action_name='Modify Quotas',
                                              resource_name='Account', config=config,
                                              status='Error')
            return False
        
        # operation log
        config = _('Project ID: %s') % data['project_id']
        api.logger.Logger(request).create(resource_type='account', action_name='Modify Quotas',
                                          resource_name='Account', config=config,
                                          status='Success')
        return True


class ChangePasswordForm(PasswordMixin, forms.SelfHandlingForm):
    id = forms.CharField(widget=forms.HiddenInput)
    name = forms.CharField(
        label=_("User Name"),
        widget=forms.TextInput(attrs={'readonly': 'readonly'}),
        required=False)

    def __init__(self, request, *args, **kwargs):
        super(ChangePasswordForm, self).__init__(request, *args, **kwargs)

        if getattr(settings, 'ENFORCE_PASSWORD_CHECK', False):
            self.fields["admin_password"] = forms.CharField(
                label=_("Admin Password"),
                widget=forms.PasswordInput(render_value=False))
            # Reorder form fields from multiple inheritance
            self.fields.keyOrder = ["id", "name", "admin_password",
                                    "password", "confirm_password"]

    @sensitive_variables('data', 'password', 'admin_password')
    def handle(self, request, data):
        user_id = data.pop('id')
        password = data.pop('password')
        admin_password = None

        # Throw away the password confirmation, we're done with it.
        data.pop('confirm_password', None)

        # Verify admin password before changing user password
        if getattr(settings, 'ENFORCE_PASSWORD_CHECK', False):
            admin_password = data.pop('admin_password')
            if not api.keystone.user_verify_admin_password(request,
                                                           admin_password):
                self.api_error(_('The admin password is incorrect.'))
                return False

        try:
            response = api.keystone.user_update_password(
                request, user_id, password)
            if user_id == request.user.id:
                return utils.logout_with_message(
                    request,
                    _('Password changed. Please log in to continue.'),
                    redirect=False)
            messages.success(request,
                             _('User password has been updated successfully.'))
        except Exception:
            # operation log
            config = _('Account name: %s') % data['name']
            api.logger.Logger(request).create(resource_type='account', action_name='Change Password',
                                              resource_name='Account', config=config,
                                              status='Error')
            response = exceptions.handle(request, ignore=True)
            messages.error(request, _('Unable to update the user password.'))

        if isinstance(response, http.HttpResponse):
            return response
        else:
            # operation log
            config = _('Account name: %s') % data['name']
            api.logger.Logger(request).create(resource_type='account', action_name='Change Password',
                                              resource_name='Account', config=config,
                                              status='Success')
            return True
