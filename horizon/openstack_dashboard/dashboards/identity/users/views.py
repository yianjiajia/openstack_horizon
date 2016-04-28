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

import operator
import random

from django.core.urlresolvers import reverse
from django.core.urlresolvers import reverse_lazy
from django.utils.decorators import method_decorator  # noqa
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.debug import sensitive_post_parameters  # noqa

from horizon import exceptions
from horizon import forms
from horizon import messages
from horizon import tables
from horizon import workflows
from horizon.utils import memoized
from horizon import views
from horizon.utils import functions as utils

from openstack_dashboard import api
from openstack_dashboard import policy

from openstack_dashboard.dashboards.identity.users \
    import forms as project_forms
from openstack_dashboard.dashboards.identity.users \
    import tables as project_tables
from openstack_dashboard.dashboards.identity.users \
    import workflows as region_workflows
from openstack_dashboard.dashboards.member import validate


class IndexView(tables.DataTableView):
    table_class = project_tables.UsersTable
    template_name = 'identity/users/index.html'
    page_title = _("Users")

    def has_more_data(self, table):
        return self._more

    def has_prev_data(self, table):
        return self._prev

    def get_data(self):
        users = []
        self._prev = False
        self._more = False
        prev_marker = self.request.GET.get(
            project_tables.UsersTable._meta.prev_pagination_param, None)
        if prev_marker is not None:
            sort_dir = 'asc'
            marker = prev_marker
        else:
            sort_dir = 'desc'
            marker = self.request.GET.get(
                project_tables.UsersTable._meta.pagination_param, None)
        page_size = utils.get_page_size(self.request)
        filters = self.get_filters({'id':  marker, 'sort_dir' :sort_dir, 'limit' :page_size+1 })

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
        elif policy.check((("identity", "identity:list_users"),),
                        self.request):
            try:
                users = api.keystone.user_list(self.request,
                                               domain=domain_context, filters = filters)
                for user in users[:]:
                    if user.name in ['nova', 'neutron', 'glance', 'cinder', 'ceilometer', 'swift', 'trove']:
                        users.remove(user)
            except Exception:
                exceptions.handle(self.request,
                                  _('Unable to retrieve user list.'))
        elif policy.check((("identity", "identity:get_user"),),
                          self.request):
            try:
                user = api.keystone.user_get(self.request,
                                             self.request.user.id)
                users.append(user)
            except Exception:
                exceptions.handle(self.request,
                                  _('Unable to retrieve user information.'))
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
            users = sorted(users, key=operator.attrgetter('created_at'), reverse = True)
        # end add pagination
        return users

    def get_filters(self, filters):
        filter_field = self.table.get_filter_field()
        filter_action = self.table._meta._filter_action
        if filter_action.is_api_filter(filter_field):
            filter_string = self.table.get_filter_string()
            if filter_field and filter_string:
                filters[filter_field] = filter_string
        return filters


class UpdateView(forms.ModalFormView):
    template_name = 'identity/users/update.html'
    modal_header = _("Update User")
    form_id = "update_user_form"
    form_class = project_forms.UpdateUserForm
    submit_label = _("Update User")
    submit_url = "horizon:identity:users:update"
    success_url = reverse_lazy('horizon:identity:users:index')
    page_title = _("Update User")

    def dispatch(self, *args, **kwargs):
        return super(UpdateView, self).dispatch(*args, **kwargs)

    @memoized.memoized_method
    def get_object(self):
        try:
            return api.keystone.user_get(self.request, self.kwargs['user_id'],
                                         admin=True)
        except Exception:
            redirect = reverse("horizon:identity:users:index")
            exceptions.handle(self.request,
                              _('Unable to retrieve user information.'),
                              redirect=redirect)

    def get_context_data(self, **kwargs):
        context = super(UpdateView, self).get_context_data(**kwargs)
        args = (self.kwargs['user_id'],)
        context['submit_url'] = reverse(self.submit_url, args=args)
        return context

    def get_initial(self):
        user = self.get_object()
        domain_id = getattr(user, "domain_id", None)
        domain_name = ''
        # Retrieve the domain name where the project belong
        if api.keystone.VERSIONS.active >= 3:
            try:
                domain = api.keystone.domain_get(self.request,
                                                 domain_id)
                domain_name = domain.name
            except Exception:
                exceptions.handle(self.request,
                                  _('Unable to retrieve project domain.'))
        if getattr(user, 'cdnLimit', None):
            cdnLimit = True
        else:
            cdnLimit = False

        random_num = random.sample('0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ', 12)
        safeCard = ''.join(random_num)
        validate.set_session(self.request, 'safeCard', safeCard)
        return {'domain_id': domain_id,
                'domain_name': domain_name,
                'id': user.id,
                'name': user.name,
                'project': user.project_id,
                'company': getattr(user, 'company', None),
                'email': getattr(user, 'email', None),
                'telephone': getattr(user, 'telephone', None),
                'contact': getattr(user, 'contact', None),
                'cdnLimit': cdnLimit,
                'regionId': user.default_region_id,
                'safeCard': safeCard}


class CreateView(forms.ModalFormView):
    template_name = 'identity/users/create.html'
    modal_header = _("Create User")
    form_id = "create_user_form"
    form_class = project_forms.CreateUserForm
    submit_label = _("Create User")
    submit_url = reverse_lazy("horizon:identity:users:create")
    success_url = reverse_lazy('horizon:identity:users:index')
    page_title = _("Create User")

    @method_decorator(sensitive_post_parameters('password',
                                                'confirm_password'))
    def dispatch(self, *args, **kwargs):
        return super(CreateView, self).dispatch(*args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(CreateView, self).get_form_kwargs()
        try:
            roles = api.keystone.role_list(self.request)
            regions = api.keystone.list_regions(self.request)
            if not self.request.user.is_superuser :
                for region in regions[:]:
                    if not region.id in self.request.user._services_region:
                        regions.remove(region)
                default_role = api.keystone.get_default_role(self.request)
                for role in roles[:]:
                    if role.name != default_role.name:
                        roles.remove(role)
        except Exception:
            redirect = reverse("horizon:identity:users:index")
            exceptions.handle(self.request,
                              _("Unable to retrieve user roles."),
                              redirect=redirect)
        roles.sort(key=operator.attrgetter("id"))
        kwargs['roles'] = roles
        kwargs['regions'] = regions
        return kwargs

    def get_initial(self):
        # Set the domain of the user
        domain = api.keystone.get_default_domain(self.request)
        default_role = api.keystone.get_default_role(self.request)
        random_num = random.sample('0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ', 12)
        safeCard = ''.join(random_num)
        validate.set_session(self.request, 'safeCard', safeCard)
        return {'domain_id': domain.id,
                'domain_name': domain.name,
                'role_id': getattr(default_role, "id", None),
                'safeCard': safeCard}


class DetailView(views.HorizonTemplateView):
    template_name = 'identity/users/detail.html'
    page_title = _("User Details")

    def get_context_data(self, **kwargs):
        context = super(DetailView, self).get_context_data(**kwargs)
        user = self.get_data()
        table = project_tables.UsersTable(self.request)
        domain_id = getattr(user, "domain_id", None)
        domain_name = ''
        if api.keystone.VERSIONS.active >= 3:
            try:
                domain = api.keystone.domain_get(self.request, domain_id)
                domain_name = domain.name
            except Exception:
                exceptions.handle(self.request,
                                  _('Unable to retrieve project domain.'))

        context["user"] = user
        context["domain_id"] = domain_id
        context["domain_name"] = domain_name
        context["url"] = self.get_redirect_url()
        context["actions"] = table.render_row_actions(user)
        return context

    @memoized.memoized_method
    def get_data(self):
        try:
            user_id = self.kwargs['user_id']
            user = api.keystone.user_get(self.request, user_id)
        except Exception:
            redirect = self.get_redirect_url()
            exceptions.handle(self.request,
                              _('Unable to retrieve user details.'),
                              redirect=redirect)
        return user

    def get_redirect_url(self):
        return reverse('horizon:identity:users:index')


class UpdateRegionsView(workflows.WorkflowView):
    workflow_class = region_workflows.UpdateRegions
    template_name = 'identity/users/regions.html'

    def get_initial(self):
        user_id = self.kwargs['user_id']
        return {'user_id': user_id, 'name': 'Update Regions'}


class ChangePasswordView(forms.ModalFormView):
    template_name = 'identity/users/change_password.html'
    modal_header = _("Change Password")
    form_id = "change_user_password_form"
    form_class = project_forms.ChangePasswordForm
    submit_url = "horizon:identity:users:change_password"
    submit_label = _("Save")
    success_url = reverse_lazy('horizon:identity:users:index')
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
            redirect = reverse("horizon:identity:users:index")
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
