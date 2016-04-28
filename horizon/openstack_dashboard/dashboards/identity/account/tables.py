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
import json

from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext_lazy
from django.conf import settings

from horizon import forms
from horizon import tables
from horizon.utils import filters

from openstack_dashboard import api
from openstack_dashboard import policy


LOG = logging.getLogger(__name__)

POLICY_CHECK = getattr(settings, "POLICY_CHECK_FUNCTION", lambda p, r: True)


class CreateAccount(tables.LinkAction):
    name = "create"
    verbose_name = _("Create Account")
    url = "horizon:identity:account:create"
    classes = ("ajax-modal",)
    icon = "plus"
    policy_rules = (("identity", "identity:create_user"),)


class DeleteAccountAction(tables.DeleteAction):
    help_text = _(
        "This Operation will delete all configuration and resources(network, images, servers, disks, VPN, firewall, keypair) and !!! Please confirm your operation.")

    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Delete User",
            u"Delete Users",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Deleted User",
            u"Deleted Users",
            count
        )

    name = "delete"
    policy_rules = (("identity", "identity:update_user"),)

    def allowed(self, request, user):
        if not api.keystone.keystone_can_edit_user():
            return False
        self.enabled = True
        if not user:
            return False
        else:
            return user.enabled

    def delele_billing_account(self, request, obj_id):
        client = api.billing.RequestClient(request)
        account = client.get_account(obj_id)
        if account:
            ret = client.api_request('/account/delete/' + account['account_id'],
                                     method='DELETE')
            user = json.loads(ret.read())
            if user['success'] != 'success':
                raise

    def delete(self, request, obj_id):
        LOG.info('Deleting User "%s".' % obj_id)
        try:
            api.keystone.user_update_enabled(request, obj_id, False)
            user = api.keystone.user_get(request, obj_id)
            api.keystone.tenant_update(request, user.default_project_id, enabled=False)
            self.delele_billing_account(request, user.default_project_id)
            # operation log
            config = _('User ID: %s') % obj_id
            api.logger.Logger(request).create(resource_type='account', action_name='Deletes User',
                                              resource_name='Account', config=config,
                                              status='Success')
        except Exception:
            # operation log
            config = _('User ID: %s') % obj_id
            api.logger.Logger(request).create(resource_type='account', action_name='Deletes User',
                                              resource_name='Account', config=config,
                                              status='Error')


class EnableAccountAction(tables.DeleteAction):
    help_text = _(
        "This Operation will enable the user and project!!! Please confirm your operation.")

    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Enable User",
            u"Enable Users",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Enabled User",
            u"Enabled Users",
            count
        )

    name = "enable"
    policy_rules = (("identity", "identity:update_user"),)

    def allowed(self, request, user):
        if not api.keystone.keystone_can_edit_user():
            return False
        self.enabled = True
        if not user:
            return False
        else:
            return not user.enabled

    def enable_billing_account(self, request, obj_id):
        client = api.billing.RequestClient(request)
        account = client.get_account(obj_id)
        if account:
            params = {}
            params['account'] = {}
            params['account']['status'] = 'normal'
            params['account']['frozen_status'] = 'normal'
            ret = client.api_request('/account/update/' + account['account_id'],
                                     method='PUT', data=json.dumps(params))
            user = json.loads(ret.read())
            if user['success'] != 'success':
                raise

    def action(self, request, obj_id):
        LOG.info('Enable User "%s".' % obj_id)
        try:
            api.keystone.user_update_enabled(request, obj_id, True)
            user = api.keystone.user_get(request, obj_id)
            api.keystone.tenant_update(request, user.default_project_id, enabled=True)
            self.enable_billing_account(request, user.default_project_id)
            # operation log
            config = _('User ID: %s') % obj_id
            api.logger.Logger(request).create(resource_type='account', action_name='Enables User',
                                              resource_name='Account', config=config,
                                              status='Success')
        except Exception:
            # operation log
            config = _('User ID: %s') % obj_id
            api.logger.Logger(request).create(resource_type='account', action_name='Enables User',
                                              resource_name='Account', config=config,
                                              status='Error')


class AccountFilterAction(tables.FilterAction):
    name = "filter_account"
    filter_type = "server"
    filter_choices = (('sname', _("Name"), True),
                      ('scompany', _("Company Name"), True),
                      ('enabled', _("Status"), True),)


class EditAccountInfoLink(tables.LinkAction):
    name = "edit"
    verbose_name = _("Edit")
    url = "horizon:identity:account:update_info"
    classes = ("ajax-modal",)
    icon = "pencil"
    policy_rules = (("identity", "identity:update_user"),)

    def allowed(self, request, datum=None):
        if not datum:
            return False
        else:
            user = api.keystone.user_get(request, datum)
            return user.enabled


class AdjustQuotaLink(tables.LinkAction):
    name = "update_quota"
    verbose_name = _("Modify Quotas")
    url = "horizon:identity:account:update_quota"
    classes = ("ajax-modal",)
    icon = "pencil"
    policy_rules = (("identity", "identity:update_project"),)

    def allowed(self, request, datum=None):
        # only display when the modified user have this region
        region_choices = []
        regions = api.keystone.list_regions_for_user(request, datum.id)
        for region in regions:
            region_choices.append(region['id'])
        if request.user.services_region not in region_choices:
            return False

        if not datum:
            return False
        else:
            user = api.keystone.user_get(request, datum)
            return user.enabled


class RoleChangeLink(tables.BatchAction):
    name = "adjust_quota"
    classes = ('btn-danger',)
    icon = "pencil"
    help_text = _("Please do it carefully!")
    policy_rules = (("identity", "identity:update_user"),)

    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Role Change",
            u"Role Changes",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Role Changed",
            u"Role Changed",
            count
        )

    def allowed(self, request, datum=None):
        policy = (("identity", "identity:create_grant"),
                  ("identity", "identity:revoke_grant"),)
        # only normal user can change their role
        # only support and admin can do this action
        if not datum:
            return False
        else:
            user = api.keystone.user_get(request, datum)
            if user.enabled:
                default_role = api.keystone.get_default_role(request)
                if user.default_role_id != default_role.id:
                    return False
                return POLICY_CHECK(policy, request)
            else:
                return False

    def action(self, request, obj_id):
        try:
            user = api.keystone.user_get(request, obj_id)
            default_user_role = api.keystone.get_default_role(request)
            default_project_admin_role = api.keystone.get_default_project_admin_role(request)

            api.keystone.remove_tenant_user_role(request, project=user.default_project_id,
                                                 user=user.id, role=default_user_role.id)
            api.keystone.user_update(request, obj_id, **{'default_role_id': default_project_admin_role.id})
            api.keystone.add_tenant_user_role(request, project=user.default_project_id,
                                              user=user.id, role=default_project_admin_role.id)
            # operation log
            config = _('Old role %s, new role %s') % (default_user_role.name, default_project_admin_role.name)
            api.logger.Logger(request).create(resource_type='account', action_name='Role_Change',
                                              resource_name='Account', config=config,
                                              status='Success')
        except Exception:
            # operation log
            config = _('Old role %s, new role %s') % (default_user_role.name, default_project_admin_role.name)
            api.logger.Logger(request).create(resource_type='account', action_name='Role_Change',
                                              resource_name='Account', config=config,
                                              status='Error')


class ChangePasswordLink(policy.PolicyTargetMixin, tables.LinkAction):
    name = "change_password"
    verbose_name = _("Change Password")
    url = "horizon:identity:account:change_password"
    classes = ("ajax-modal",)
    icon = "key"
    policy_rules = (("identity", "identity:change_password"),)
    policy_target_attrs = (("user_id", "id"),)

    def allowed(self, request, datum=None):
        if not datum:
            return False
        else:
            user = api.keystone.user_get(request, datum)
            return user.enabled and api.keystone.keystone_can_edit_user()


class UpdateRegionsLink(policy.PolicyTargetMixin, tables.LinkAction):
    name = "regions"
    verbose_name = _("Update Regions")
    url = "horizon:identity:account:regions"
    classes = ("ajax-modal",)
    icon = "pencil"
    policy_rules = (("identity", "identity:update_user_regions"),)

    def allowed(self, request, datum=None):
        if not datum:
            return False
        else:
            user = api.keystone.user_get(request, datum)
            return user.enabled

class UpdateMembersLink(tables.LinkAction):
    name = "users"
    verbose_name = _("Manage Members")
    url = "horizon:identity:account:update_member"
    classes = ("ajax-modal",)
    icon = "pencil"
    policy_rules = (("identity", "identity:list_users"),
                    ("identity", "identity:list_grants"))

    def allowed(self, request, datum=None):
        if not datum:
            return False
        else:
            user = api.keystone.user_get(request, datum)
            return user.enabled

STATUS_DISPLAY_CHOICES = (
    (False, _("Delete")),
    (True, _("Normal")),
)


class AccountsTable(tables.DataTable):
    id = tables.Column('id', hidden=True)
    # project_id = tables.Column('project_id', hidden=True)
    name = tables.Column('name',
                         verbose_name=_('User Name'),
                         form_field=forms.CharField(),
                         link='horizon:identity:account:detail'
                         )
    company = tables.Column('company',
                            verbose_name=_('Company Name'),
                            form_field=forms.CharField())

    # email = tables.Column('email', verbose_name=_('Email'),
    #                       form_field=forms.CharField(required=False),
    #                       filters=(lambda v: defaultfilters
    #                                .default_if_none(v, ""),
    #                                defaultfilters.escape,
    #                                defaultfilters.urlize)
    #                       )
    enabled = tables.Column('enabled', verbose_name=_('Status'),
                            # status=True,
                            # status_choices=STATUS_CHOICES,
                            display_choices=STATUS_DISPLAY_CHOICES,
                            empty_value="False")
    created_at = tables.Column('created_at',
                               verbose_name=_('Created_at'),
                               filters=[filters.parse_isotime])

    class Meta(object):
        name = "accounts"
        verbose_name = _("AccountList")
        table_actions = (AccountFilterAction, CreateAccount)
        row_actions = (EditAccountInfoLink, AdjustQuotaLink, UpdateRegionsLink, UpdateMembersLink,
                       RoleChangeLink, ChangePasswordLink, DeleteAccountAction, EnableAccountAction)
