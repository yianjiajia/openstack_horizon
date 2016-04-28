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

import operator
import random

from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse_lazy
from django.core.urlresolvers import reverse
from django.utils.decorators import method_decorator  # noqa
from django.views.decorators.debug import sensitive_post_parameters  # noqa

from horizon import exceptions
from horizon import tables
from horizon import workflows
from horizon import messages
from horizon.utils import functions as utils
from horizon.utils import memoized
from horizon import forms
from horizon import views

from openstack_dashboard import policy
from openstack_dashboard import api
from openstack_dashboard.dashboards.identity.account \
    import tables as account_tables
from openstack_dashboard.dashboards.identity.account import \
    workflows as account_workflow
from openstack_dashboard.dashboards.identity.account import \
    forms as account_forms
from openstack_dashboard.dashboards.member import validate
from openstack_dashboard.usage import quotas
from openstack_dashboard.api import billing
from openstack_dashboard.dashboards.identity.account.tables import STATUS_DISPLAY_CHOICES
from openstack_dashboard.dashboards.identity.users.views import UpdateRegionsView


class IndexView(tables.DataTableView):
    table_class = account_tables.AccountsTable
    template_name = 'identity/account/index.html'
    page_title = _("AccountList")

    def has_more_data(self, table):
        return self._more

    def has_prev_data(self, table):
        return self._prev

    def get_data(self):
        users = []
        self._prev = False
        self._more = False
        prev_marker = self.request.GET.get(
            account_tables.AccountsTable._meta.prev_pagination_param, None)
        if prev_marker is not None:
            sort_dir = 'asc'
            marker = prev_marker
        else:
            sort_dir = 'desc'
            marker = self.request.GET.get(
                account_tables.AccountsTable._meta.pagination_param, None)
        page_size = utils.get_page_size(self.request)
        filters = self.get_filters({'id': marker, 'sort_dir': sort_dir, 'limit': page_size + 1})

        domain_context = self.request.session.get('domain_context', None)
        if policy.check((("identity", "identity:list_children_projects"),),
                        self.request):
            try:
                parent_id=self.request.user.id
                filters['parent_id'] = parent_id
                users = api.keystone.user_list(self.request,
                                               domain=domain_context,
                                               filters=filters)
            except Exception:
                exceptions.handle(self.request,
                                  _('Unable to retrieve user list.'))
        elif policy.check((("identity", "identity:list_users"),), self.request) or \
                policy.check((("identity", "support_required"),), self.request):
            try:
                users = api.keystone.user_list(self.request,
                                               domain=domain_context, filters=filters)
                for user in users[:]:
                    if user.name in ['nova', 'neutron', 'glance', 'cinder', 'ceilometer', 'swift', 'trove']:
                        users.remove(user)
            except Exception:
                exceptions.handle(self.request,
                                  _('Unable to retrieve user list.'))
        else:
            msg = _("Insufficient privilege level to view user information.")
            messages.info(self.request, msg)

        # add pagination here
        self._prev = False
        self._more = False

        if len(users) > page_size:
            users.pop(-1)
            self._more = True
            if marker is not None:
                self._prev = True
        elif sort_dir == 'asc' and marker is not None:
            self._more = True
        elif marker is not None:
            self._prev = True

        if 'asc' == sort_dir:
            users = sorted(users, key=operator.attrgetter('created_at'), reverse=True)
        # end add pagination
        return users

    def get_filters(self, filters):
        filter_field = self.table.get_filter_field()
        filter_action = self.table._meta._filter_action
        if filter_action.is_api_filter(filter_field):
            filter_string = self.table.get_filter_string()
            if filter_field == 'enabled' and filter_string and (0x4e00 <= ord(filter_string[0]) < 0x9fa6):
                filter_string = [x[0] for x in STATUS_DISPLAY_CHOICES if x[1] == filter_string]
                if filter_string:
                    filter_string = filter_string[0]
                else:
                    filter_string = 'not_make_sense'
            if filter_field and filter_string:
                filters[filter_field] = filter_string
        return filters


class UpdateInfoView(forms.ModalFormView):
    template_name = 'identity/account/update.html'
    modal_header = _("Update Account")
    form_id = "update_account_form"
    form_class = account_forms.UpdateAccountInfoForm
    submit_label = _("Update Account")
    submit_url = "horizon:identity:account:update_info"
    success_url = reverse_lazy('horizon:identity:account:index')
    page_title = _("Update Account")

    @memoized.memoized_method
    def get_object(self):
        try:
            return api.keystone.user_get(self.request, self.kwargs['user_id'],
                                         )
        except Exception:
            redirect = reverse("horizon:identity:account:index")
            exceptions.handle(self.request,
                              _('Unable to retrieve user information.'),
                              redirect=redirect)

    def get_context_data(self, **kwargs):
        context = super(UpdateInfoView, self).get_context_data(**kwargs)
        args = (self.kwargs['user_id'],)
        context['submit_url'] = reverse(self.submit_url, args=args)
        return context

    def get_initial(self):
        initial = super(UpdateInfoView, self).get_initial()
        user = self.get_object()
        initial['id'] = user.id
        initial['project_id'] = user.default_project_id
        initial['regionId'] = user.default_region_id
        initial['company'] = getattr(user, 'company', None)
        initial['email'] = getattr(user, 'email', None)
        initial['telephone'] = getattr(user, 'telephone', None)
        try:
            project = api.keystone.tenant_get(self.request, user.default_project_id)
        except Exception:
            redirect = reverse("horizon:identity:account:index")
            exceptions.handle(self.request,
                              _('Unable to retrieve project information.'),
                              redirect=redirect)
        initial['project_name'] = project.name
        random_num = random.sample('0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ', 12)
        safeCard = ''.join(random_num)
        validate.set_session(self.request, 'safeCard', safeCard)
        initial['safeCard'] = safeCard
        return initial


class UpdateQuotaView(forms.ModalFormView):
    template_name = 'identity/account/update_quota.html'
    modal_header = _("Modify Quotas")
    form_id = "update_quota_form"
    form_class = account_forms.UpdateQuotaForm
    submit_label = _("Modify Quotas")
    submit_url = "horizon:identity:account:update_quota"
    success_url = reverse_lazy('horizon:identity:account:index')
    page_title = _("Modify Quotas")

    @memoized.memoized_method
    def get_object(self):
        try:
            return api.keystone.user_get(self.request, self.kwargs['user_id'],
                                         )
        except Exception:
            redirect = reverse("horizon:identity:account:index")
            exceptions.handle(self.request,
                              _('Unable to retrieve user information.'),
                              redirect=redirect)

    def get_context_data(self, **kwargs):
        context = super(UpdateQuotaView, self).get_context_data(**kwargs)
        args = (self.kwargs['user_id'],)
        context['submit_url'] = reverse(self.submit_url, args=args)
        return context

    def get_initial(self):
        initial = super(UpdateQuotaView, self).get_initial()
        user = self.get_object()

        # try:
        #     user_account = billing.RequestClient(self.request).get_account(project_id=user.project_id)
        # except Exception:
        #     redirect = reverse("horizon:identity:account:index")
        #     exceptions.handle(self.request,
        #                       _('Unable to retrieve user account details.'),
        #                       redirect=redirect)
        initial['user_id'] = user.id
        initial['region_id'] = self.request.user.services_region
        initial['project_id'] = user.default_project_id
        # initial['user_type'] = user_account['type']
        # initial['credit_line'] = user_account['credit_line']
        try:
            # get initial project quota
            quota_data = quotas.get_tenant_quota_data(self.request,
                                                      tenant_id=user.default_project_id,
                                                      region=self.request.user.services_region)
            if api.base.is_service_enabled(self.request, 'network') and \
                    api.neutron.is_quotas_extension_supported(self.request):
                quota_data += api.neutron.tenant_quota_get(
                    self.request, tenant_id=user.default_project_id, region=self.request.user.services_region)
            for field in quotas.QUOTA_FIELDS:
                initial[field] = quota_data.get(field).limit
        except Exception:
            redirect = reverse("horizon:identity:account:index")
            exceptions.handle(self.request,
                              _('Unable to retrieve project details.'),
                              redirect=redirect)
        return initial


class ChangePasswordView(forms.ModalFormView):
    template_name = 'identity/account/change_password.html'
    modal_header = _("Change Password")
    form_id = "change_user_password_form"
    form_class = account_forms.ChangePasswordForm
    submit_url = "horizon:identity:account:change_password"
    submit_label = _("Save")
    success_url = reverse_lazy('horizon:identity:account:index')
    page_title = _("Change Password")

    @method_decorator(sensitive_post_parameters('password',
                                                'confirm_password'))
    def dispatch(self, *args, **kwargs):
        return super(ChangePasswordView, self).dispatch(*args, **kwargs)

    @memoized.memoized_method
    def get_object(self):
        try:
            return api.keystone.user_get(self.request, self.kwargs['user_id'],
                                         admin=True)
        except Exception:
            redirect = reverse("horizon:identity:account:index")
            exceptions.handle(self.request,
                              _('Unable to retrieve user information.'),
                              redirect=redirect)

    def get_context_data(self, **kwargs):
        context = super(ChangePasswordView, self).get_context_data(**kwargs)
        args = (self.kwargs['user_id'],)
        context['submit_url'] = reverse(self.submit_url, args=args)
        return context

    def get_initial(self):
        user = self.get_object()
        return {'id': self.kwargs['user_id'],
                'name': user.name}


class UpdateRegionsView(UpdateRegionsView):
    workflow_class = account_workflow.UpdateRegions


class UpdateMemberView(workflows.WorkflowView):
    workflow_class = account_workflow.UpdateMember

    def get_initial(self):
        user_id = self.kwargs['user_id']
        user = api.keystone.user_get(self.request, user_id)
        project_id = user.default_project_id
        return {'user_id': user_id, 'project_id': project_id}


class CreateView(workflows.WorkflowView):
    workflow_class = account_workflow.CreateAccount


class DetailView(views.HorizonTemplateView):
    template_name = 'identity/account/detail.html'
    page_title = _("User Details")

    def get_context_data(self, **kwargs):
        context = super(DetailView, self).get_context_data(**kwargs)
        user = self.get_data()
        context["user"] = user
        return context

    @memoized.memoized_method
    def get_data(self):
        try:
            user_id = self.kwargs['user_id']
            user = api.keystone.user_get(self.request, user_id)
            project = api.keystone.tenant_get(self.request, user.default_project_id)
            regions = api.keystone.list_regions_for_user(self.request, user_id)
            roles = api.keystone.roles_for_user(self.request, user_id, user.default_project_id)
            role_name = [r.name for r in roles if r.id == user.default_role_id][0]
            setattr(user, 'company', getattr(user, 'company', None))
            setattr(user, 'roles', role_name)

            # TODO: get usage info
            usages = []
            if regions:
                region_names = [r['description'] for r in regions]
                setattr(user, 'regions', region_names)
                
                for r in regions:
                    usage = quotas.tenant_quota_usages(
                        self.request, tenant_id=user.default_project_id, region=r['id'])
                    # fake a region quota for display
                    qr = api.base.Quota('region', r['id'])
                    usage.add_quota(qr)
                    usages.append(usage)
            setattr(user, 'usages', usages)
            if project:
                if project.name:
                    setattr(user, 'project_name', project.name)
        except Exception:
            redirect = self.get_redirect_url()
            exceptions.handle(self.request,
                              _('Unable to retrieve user details.'),
                              redirect=redirect)
        return user

    def get_redirect_url(self):
        return reverse('horizon:identity:account:index')

