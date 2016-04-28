# coding=utf-8
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

import logging
import random
import traceback

from django.utils.translation import ugettext_lazy as _
from django.forms import ValidationError  # noqa
from django.views.decorators.debug import sensitive_variables  # noqa
from django.core.validators import MaxValueValidator

from horizon import workflows
from horizon import forms
from horizon.utils import validators
from horizon import exceptions
from horizon import messages
from django.conf import settings

from openstack_auth import utils as auth_utils
from openstack_dashboard import policy
from openstack_dashboard import api
from openstack_dashboard.api import base
from openstack_dashboard.api import nova
from openstack_dashboard.api import cinder
from openstack_dashboard.api import billing
from openstack_dashboard.usage import quotas
from openstack_dashboard.api.member.member import UserCenter
from openstack_dashboard.dashboards.member import validate
from openstack_dashboard.dashboards.identity.users.workflows import UpdateRegions
from openstack_dashboard.dashboards.identity.projects.workflows import UpdateProject
from openstack_dashboard.dashboards.identity.projects.workflows import UpdateProjectMembers

import keystoneclient.openstack.common.apiclient.exceptions as kc_exceptions

LOG = logging.getLogger(__name__)

INDUSTRY_CHOICES = [('教育/培训', '教育/培训'),
                    ('电子商务', '电子商务'),
                    ('对外贸易', '对外贸易'),
                    ('游戏', '游戏'),
                    ('互联网金融', '互联网金融'),
                    ('互联网广告', '互联网广告'),
                    ('在线医疗', '在线医疗'),
                    ('在线旅游', '在线旅游'),
                    ('制造', '制造'),
                    ('其他', '其他')]


class AccountInfoAction(workflows.Action):
    domain_id = forms.CharField(label=_("Domain ID"),
                                initial='default',
                                required=False,
                                widget=forms.HiddenInput())
    company = forms.CharField(label=_("Company Name"))
    industry = forms.ChoiceField(label=_("Industry"),
                                 choices=INDUSTRY_CHOICES)

    name = forms.CharField(label=_("Name"),
                           max_length=64)
    email = forms.EmailField(
        label=_("Email"),
        required=True)
    password = forms.RegexField(
        label=_("Password"),
        widget=forms.PasswordInput(render_value=False),
        regex=validators.password_validator(),
        error_messages={'invalid': validators.password_validator_msg()})
    confirm_password = forms.CharField(
        label=_("Confirm Password"),
        widget=forms.PasswordInput(render_value=False))
    telephone = forms.CharField(
        label=_("Telephone"),
        required=True)
    default_role_id = forms.ChoiceField(label=_("Role"),
                                        required=False)
    safeCard = forms.CharField(widget=forms.HiddenInput(),
                               required=False)
    no_autocomplete = True

    def __init__(self, request, *args, **kwargs):
        super(AccountInfoAction, self).__init__(request,
                                                *args,
                                                **kwargs)
        random_num = random.sample('0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ', 12)
        safeCard = ''.join(random_num)
        validate.set_session(self.request, 'safeCard', safeCard)
        self.fields['safeCard'].initial = safeCard
        if not request.user.is_superuser:
            self.fields['default_role_id'].widget = forms.HiddenInput()
        else:
            try:
                roles = api.keystone.role_list(request)
                role_choices = [(r.id, r.name) for r in roles]
                if role_choices:
                    default_role_name = settings.OPENSTACK_KEYSTONE_DEFAULT_ROLE
                    role_choices = [r for r in role_choices if r[1] == default_role_name] + \
                                   [r for r in role_choices if r[1] != default_role_name]
                    self.fields['default_role_id'].choices = role_choices
                    self.fields['default_role_id'].required = True
                else:
                    self.fields['default_role_id'].choices = [('', _("No roles"))]
            except Exception:
                self.fields['default_role_id'].choices = [('', _("No roles"))]
                exceptions.handle(request, _('Failed to retrieve role list'))

    def clean(self):
        '''Check to make sure password fields match.'''
        data = super(forms.Form, self).clean()
        if 'password' in data:
            if data['password'] != data.get('confirm_password', None):
                raise ValidationError(_('Passwords do not match.'))

        company = data['company']
        user = api.keystone.user_list(self.request, filters={'company': company})
        if user:
            msg = (_('Company with name %s already exsit, please use another one.') %
                   company)
            raise forms.ValidationError(msg)
        return data

    class Meta(object):
        name = _("Account Info")


class AccountInfoStep(workflows.Step):
    template_name = 'identity/account/_createaccount_info_step.html'
    action_class = AccountInfoAction
    contributes = ('domain_id', 'company', 'industry', 'name', 'email', 'telephone', 'password', 'default_role_id')


class AccountQuotaAction(workflows.Action):
    user_type = forms.ChoiceField(
        label=_("Account Type"),
        required=True,
        choices=[('normal', _("Normal User")), ('credit', _("Credit User"))],
        widget=forms.Select(
            attrs={
                'class': 'switchable',
                'data-slug': 'user_type'
            }
        )
    )
    credit_line = forms.FloatField(
        label=_("Credit Line"),
        required=False,
        min_value=0.0,
        initial=settings.GIFT_BANLANCE,
        widget=forms.TextInput(
            attrs={
                'class': 'switched',
                'data-switch-on': 'user_type',
                'data-user_type-credit': _('Credit Line'),
                'data-is-required': 'true',
            }))
    adjust_quota = forms.BooleanField(
        label=_("Adjust Quota"),
        required=False,
        initial=True,
        widget=forms.CheckboxInput(
            attrs={
                'class': 'switchable',
                'data-slug': 'adjust_quota',
                'data-hide-on-checked': 'false'
            }
        )
    )
    instances = forms.IntegerField(min_value=-1, initial=settings.QUOTA_DEFAULI['nova']['instances'],
                                   label=_("Instances"),
                                   required=True,
                                   widget=forms.TextInput(attrs={
                                       'class': 'switched',
                                       'data-switch-on': 'adjust_quota',
                                       'data-is-required': 'true',
                                       'style': 'width 10%'
                                   }))

    cores = forms.IntegerField(min_value=2, initial=settings.QUOTA_DEFAULI['nova']['cores'],
                               label=_("VCPUs"),
                               required=True,
                               widget=forms.TextInput(attrs={
                                   'class': 'switched',
                                   'data-switch-on': 'adjust_quota',
                                   'data-is-required': 'true'
                               }))
    ram = forms.IntegerField(min_value=-1, initial=settings.QUOTA_DEFAULI['nova']['ram'],
                             label=_("RAM (MB)"),
                             required=True,
                             widget=forms.TextInput(attrs={
                                 'class': 'switched',
                                 'data-switch-on': 'adjust_quota',
                                 'data-is-required': 'true'
                             }))
    volumes = forms.IntegerField(min_value=-1, initial=settings.QUOTA_DEFAULI['cinder']['volumes'],
                                 label=_("Volumes"),
                                 required=True,
                                 widget=forms.TextInput(attrs={
                                     'class': 'switched',
                                     'data-switch-on': 'adjust_quota',
                                     'data-is-required': 'true'
                                 }))
    snapshots = forms.IntegerField(min_value=-1, initial=settings.QUOTA_DEFAULI['cinder']['snapshots'],
                                   label=_("Volume Snapshots"),
                                   required=True,
                                   widget=forms.TextInput(attrs={
                                       'class': 'switched',
                                       'data-switch-on': 'adjust_quota',
                                       'data-is-required': 'true'
                                   }))
    volume_gigabytes = forms.IntegerField(
        min_value=-1, initial=settings.QUOTA_DEFAULI['cinder']['volume_gigabytes'],
        label=_("Size of Volumes(GB)"),
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'switched',
            'data-switch-on': 'adjust_quota',
            'data-is-required': 'true'
        }))

    snapshot_gigabytes = forms.IntegerField(
        min_value=-1, initial=settings.QUOTA_DEFAULI['cinder']['snapshot_gigabytes'],
        label=_("Size of Snapshots (GB)"),
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'switched',
            'data-switch-on': 'adjust_quota',
            'data-is-required': 'true'
        }))

    floatingip = forms.IntegerField(min_value=-1, initial=settings.QUOTA_DEFAULI['neutron']['floatingip'],
                                    label=_("Floating IPs"),
                                    required=True,
                                    widget=forms.TextInput(attrs={
                                        'class': 'switched',
                                        'data-switch-on': 'adjust_quota',
                                        'data-is-required': 'true'
                                    }))
    network = forms.IntegerField(min_value=-1, initial=settings.QUOTA_DEFAULI['neutron']['network'],
                                 label=_("Networks"),
                                 required=True,
                                 widget=forms.TextInput(attrs={
                                     'class': 'switched',
                                     'data-switch-on': 'adjust_quota',
                                     'data-is-required': 'true'
                                 }))
    router = forms.IntegerField(min_value=-1, initial=settings.QUOTA_DEFAULI['neutron']['router'],
                                label=_("Routers"),
                                required=True,
                                widget=forms.TextInput(attrs={
                                    'class': 'switched',
                                    'data-switch-on': 'adjust_quota',
                                    'data-is-required': 'true'
                                }))
    subnet = forms.IntegerField(min_value=-1, initial=settings.QUOTA_DEFAULI['neutron']['subnet'],
                                label=_("Subnets"),
                                required=True,
                                widget=forms.TextInput(attrs={
                                    'class': 'switched',
                                    'data-switch-on': 'adjust_quota',
                                    'data-is-required': 'true'
                                }))
    pool = forms.IntegerField(min_value=-1, initial=settings.QUOTA_DEFAULI['neutron']['pool'],
                              label=_("Loadbalancers"),
                              required=True,
                              widget=forms.TextInput(attrs={
                                  'class': 'switched',
                                  'data-switch-on': 'adjust_quota',
                                  'data-is-required': 'true'
                              }))
    bandwidth = forms.IntegerField(required=False, widget=forms.HiddenInput,
                                   initial=settings.QUOTA_DEFAULI['neutron']['bandwidth'], )

    def __init__(self, request, *args, **kwargs):
        super(AccountQuotaAction, self).__init__(request, *args, **kwargs)
        if policy.check((("identity", "project_admin_required"),), self.request):
            self.fields['credit_line'].validators.append(MaxValueValidator(settings.UPPER_CREDIT_LINE_FOR_PROJECT_ADMIN))
            self.fields['credit_line'].help_text = _('credit line is between 0~%s') % settings.UPPER_CREDIT_LINE_FOR_PROJECT_ADMIN

    class Meta(object):
        name = _("Account Quota")


class AccountQuotaStep(workflows.Step):
    template_name = 'identity/account/_createaccount_quota_step.html'
    action_class = AccountQuotaAction
    contributes = ('user_type', 'credit_line', 'adjust_quota',
                   'cores', 'instances', 'ram',
                   'volumes', 'snapshots', 'volume_gigabytes', 'snapshot_gigabytes',
                   'network', 'router', 'subnet', 'pool', 'floatingip', 'bandwidth')


NOVA_QUOTA_FIELDS = ("cores", "instances", "ram")
NEUTRON_QUOTA_FIELDS = ("network", "subnet", "router", "floatingip", "pool", "bandwidth")


class CreateAccount(workflows.Workflow):
    wizard = True
    slug = "create_account"
    name = _("Create Account")
    finalize_button_name = _("Create")
    success_message = _('Created account %s.')
    failure_message = _('Unable to create account %s.')
    success_url = "horizon:identity:account:index"
    default_steps = (AccountInfoStep, AccountQuotaStep)

    def format_status_message(self, message):
        name = self.context.get('name')
        return message % name

    # We have to protect the entire "data" dict because it contains the
    # password and confirm_password strings.
    @sensitive_variables('data')
    def _create_user(self, request, data):
        domain = api.keystone.get_default_domain(self.request)
        try:
            region_id = request.user.services_region
            data['region_id'] = region_id
            LOG.info('Creating user with name "%s"' % data['name'])
            new_user = api.keystone.user_create(request,
                                                company=data['company'],
                                                industry=data['industry'],
                                                name=data['name'],
                                                email=data['email'],
                                                password=data['password'],
                                                telephone=data['telephone'],
                                                region_id=data['region_id'],
                                                project=data['project'],
                                                enabled=True,
                                                domain=domain.id,
                                                parent_id=request.user.id,
                                                default_role_id=data['default_role_id']
                                                )
            if data['user_type'] == 'normal':
                credit_line = 0.0
            else:
                credit_line = data['credit_line']
            try:
                gift_balance = getattr(settings, "GIFT_BANLANCE", 0)
                logging.error('settings set is %s', gift_balance)
            except Exception as e:
                logging.error('settings not set gift_balance')
            data_toBilling = {
                "account": {'account_id': '', 'username': data['name'], 'cash_balance': 0, 'gift_balance': gift_balance,
                            'type': data['user_type'], 'credit_line': credit_line, 'status': 'normal',
                            'user_id': new_user.id, 'project_id': data['project']}}
            try:
                billingClinect = billing.BillingUser(request)
                billingUser = billingClinect.create_billingUser(data_toBilling)
                if not billingUser:
                    userC = UserCenter()
                    userC.deleteUser(new_user)
                    new_user = None
            except Exception as e:
                LOG.error(str(e))
                LOG.error(traceback.format_exc())
                userC = UserCenter()
                userC.deleteUser(new_user)
                new_user = None
            return new_user
        except exceptions.Conflict:
            msg = _('User name "%s" is already used.') % data['name']
            messages.error(request, msg)
        except Exception:
            exceptions.handle(request, _('Unable to create user.'))

    def _create_project(self, request, data):
        # create the project
        domain_id = data['domain_id']
        try:
            parent_id = request.user.project_id
            self.object = api.keystone.tenant_create(request,
                                                     name=data['company'],
                                                     domain=domain_id,
                                                     parent_id=parent_id)
            return self.object
        except kc_exceptions.Conflict:
            failure_message_conflict = _('Unable to create project "%s", project name conflict.')
            exceptions.handle(request, message=failure_message_conflict % data['name'], ignore=False)
            raise
        except Exception:
            exceptions.handle(request, ignore=True)
            raise

    def _update_project_members(self, request, user_id, project_id, default_role_id=None):
        try:
            api.keystone.add_tenant_user_role(request,
                                              project=project_id,
                                              user=user_id,
                                              role=default_role_id)

        except Exception:
            exceptions.handle(request,
                              _('Failed to add user %s to project %s with role %s.')
                              % (user_id, project_id, default_role_id))
            raise
        finally:
            auth_utils.remove_project_cache(request.user.token.id)

    def _update_project_quota(self, request, data, project_id):
        # Update the project quota.
        nova_data = dict(
            [(key, data[key]) for key in NOVA_QUOTA_FIELDS])
        data['region_id'] = request.user.services_region
        try:
            nova.tenant_quota_update(request, project_id, region=data['region_id'], **nova_data)

            if base.is_service_enabled(request, 'volume'):
                cinder_data = dict([(key, data[key]) for key in
                                    quotas.CINDER_QUOTA_FIELDS])
                cinder.tenant_quota_update(request,
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
            raise
            exceptions.handle(request, _('Unable to set project quotas.'))

    def handle(self, request, data):
        try:
            project = self._create_project(request, data)
            if not project:
                raise
            # set primary project for user
            data['project'] = project.id

            # set default_role
            if not data['default_role_id']:
                default_role = api.keystone.get_default_role(request)
                data['default_role_id'] = default_role.id

            user = self._create_user(request, data)
            if not user:
                # also delete the project
                try:
                    api.keystone.tenant_delete(request, project.id)
                except Exception as e:
                    LOG.error(str(e))
                    LOG.error(traceback.format_exc())
                    exceptions.handle(request, _('Unable to rollback created project.'))
                raise
            user_id = user.id
            project_id = project.id
            self._update_project_members(request, user_id, project_id, data['default_role_id'])
            self._update_project_quota(request, data, project_id)

            # operation log
            config = _('Account name: %s') % data['name']
            api.logger.Logger(request).create(resource_type='account', action_name='Create Account',
                                              resource_name='Account', config=config,
                                              status='Success')
        except Exception:
            # operation log
            config = _('Account name: %s') % data['name']
            api.logger.Logger(request).create(resource_type='account', action_name='Create Account',
                                              resource_name='Account', config=config,
                                              status='Error')
            return False
        return True


class UpdateRegions(UpdateRegions):
    success_url = "horizon:identity:account:index"


class UpdateProjectMembers(UpdateProjectMembers):
    depends_on = ('project_id',)


class UpdateMember(UpdateProject):
    slug = "update_member"
    name = _("Manage Members")
    finalize_button_name = _("Save")
    success_message = _('Member Updated.')
    failure_message = _('Unable to Update Member.')
    success_url = "horizon:identity:account:index"
    default_steps = (UpdateProjectMembers,)

    def handle(self, request, data):
        ret = super(UpdateMember, self)._update_project_members(request, data, data['project_id'])
        if not ret:
            # operation log
            config = _('Project ID: %s') % data['project_id']
            api.logger.Logger(request).create(resource_type='account', action_name='Manage Members',
                                              resource_name='Account', config=config,
                                              status='Error')
            return False

        # operation log
        config = _('Project ID: %s') % data['project_id']
        api.logger.Logger(request).create(resource_type='account', action_name='Manage Members',
                                          resource_name='Account', config=config,
                                          status='Success')

        return True

    def format_status_message(self, message):
        return message
