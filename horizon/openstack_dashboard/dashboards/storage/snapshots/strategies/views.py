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

from django.core.urlresolvers import reverse
from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import forms
from horizon import tabs
from horizon.utils import memoized

from openstack_dashboard import api

from openstack_dashboard.dashboards.storage.snapshots.strategies import forms as project_forms
from openstack_dashboard.dashboards.storage.snapshots.strategies import tabs as project_tabs
from openstack_dashboard.dashboards.storage.snapshots import tables as project_tables

class CreateSnapshotStrategyView(forms.ModalFormView):
    form_class = project_forms.CreateSnapshotStrategyForm
    modal_header = _("Create Strategy")
    template_name = 'storage/snapshots/strategies/create.html'
    submit_label = _("Create Strategy")
    submit_url = reverse_lazy("horizon:storage:snapshots:strategies:create_strategy")
    success_url = reverse_lazy('horizon:storage:snapshots:strategies_tab')
    page_title = _("Create Volume Auto Snapshot Strategy")

class DetailView(tabs.TabView):
    tab_group_class = project_tabs.SnapshotStrategyDetailTabs
    template_name = 'storage/snapshots/strategies/detail.html'
    page_title = _("Snapshot Strategy Details")

    def get_context_data(self, **kwargs):
        context = super(DetailView, self).get_context_data(**kwargs)
        strategy = self.get_data()
        table = project_tables.SnapshotStrategiesTable(self.request)
        context["strategy"] = strategy
        context["url"] = self.get_redirect_url()
        context["actions"] = table.render_row_actions(strategy)
        return context

    @memoized.memoized_method
    def get_data(self):
        try:
            strategy_id = self.kwargs['strategy_id']
            strategy = api.cinder.volume_snapshot_strategy_get(self.request,
                                                      strategy_id)
        except Exception:
            redirect = self.get_redirect_url()
            exceptions.handle(self.request,
                              _('Unable to retrieve snapshot strategy details.'),
                              redirect=redirect)
        return strategy

    @staticmethod
    def get_redirect_url():
        return reverse('horizon:storage:snapshots:index')

    def get_tabs(self, request, *args, **kwargs):
        strategy = self.get_data()
        return self.tab_group_class(request, strategy=strategy, **kwargs)

class UpdateView(forms.ModalFormView):
    form_class = project_forms.UpdateForm
    form_id = "update_snapshot_strategy_form"
    modal_header = _("Edit Snapshot Strategy")
    template_name = 'storage/snapshots/strategies/update.html'
    submit_label = _("Save Changes")
    submit_url = "horizon:storage:snapshots:strategies:update"
    success_url = reverse_lazy("horizon:storage:snapshots:index")
    page_title = _("Edit Snapshot")

    @memoized.memoized_method
    def get_object(self):
        strategy_id = self.kwargs['strategy_id']
        try:
            self._object = api.cinder.volume_snapshot_strategy_get(self.request,
                                                          strategy_id)
        except Exception:
            msg = _('Unable to retrieve volume snapshot strategy.')
            url = reverse('horizon:storage:snapshots:index')
            exceptions.handle(self.request, msg, redirect=url)
        return self._object

    def get_context_data(self, **kwargs):
        context = super(UpdateView, self).get_context_data(**kwargs)
        context['strategy'] = self.get_object()
        args = (self.kwargs['strategy_id'],)
        context['submit_url'] = reverse(self.submit_url, args=args)
        return context

    def get_initial(self):
        strategy = self.get_object()
        return {'strategy_id': self.kwargs["strategy_id"],
                'name': strategy.name,
                'volume_id': strategy.volume_id,
                'snapshot_at': strategy.snapshot_at,
                'keep_last_sunday': strategy.keep_last_sunday,
                'max_keep_number': strategy.max_keep_number,
                'status': strategy.status}
