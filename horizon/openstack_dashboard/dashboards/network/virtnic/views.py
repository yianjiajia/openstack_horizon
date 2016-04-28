
"""
Views for managing Neutron virtnic.
"""
from django.core.urlresolvers import reverse
from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import forms
from horizon import tables
from horizon import tabs
from horizon.utils import memoized

from openstack_dashboard import api
from django.utils.datastructures import SortedDict


from openstack_dashboard.dashboards.network.virtnic \
    import tables as project_tables
from openstack_dashboard.dashboards.network.virtnic\
    import forms as project_forms

from openstack_dashboard.dashboards.network.virtnic \
    import tabs as project_tabs


class IndexView(tables.DataTableView):
    
    table_class = project_tables.VirtnicTable
    template_name = 'network/virtnic/index.html'
    page_title = _("Virtnics")

    def get_data(self):
        try:
#             tenant_id = self.request.user.tenant_id
#             print self.request.user.tenant_id
            tenant_id = self.request.user.tenant_id
            search_opts = {"flag": "manual", "tenant_id":tenant_id}
            ports = api.neutron.port_list(self.request, **search_opts)
            floating_ips = api.network.tenant_floating_ip_list(self.request)
            
        except Exception:
            ports = []
            floating_ips = []
            msg = _('virtnic list can not be retrieved.')
            exceptions.handle(self.request, msg)
        fix_floating_ips=[]
        if floating_ips:
            fix_floating_ips = SortedDict([(floating_ip.port_id, floating_ip) 
                                          for floating_ip in floating_ips
                                          if floating_ip["port_id"]])
           
        if ports:
            ports_new = []
            for port in ports:
                if port.id in fix_floating_ips:
                    port.fix_floating_ip=fix_floating_ips[port.id]
                    
                if port["device_id"]:
                    try:
                        port.host = api.nova.server_get(self.request, port["device_id"])
                    except Exception:
                        msg = _('server can not be retrieved.')
#                         exceptions.handle(self.request, msg)
                if port["network_id"]:
                    try:
                        port.network = api.neutron.network_get(self.request, port["network_id"])
                    except Exception:
                        msg = _('network can not be retrieved.')
#                         exceptions.handle(self.request, msg)
                ports_new.append(port)
            return ports_new
        return ports


class CreateView(forms.ModalFormView):
    form_class = project_forms.CreateForm
    form_id = "create_virtnic_form"
    modal_header = _("Create Virtnic")
    template_name = 'network/virtnic/create.html'
    success_url = reverse_lazy("horizon:network:virtnic:index")
    page_title = _("Create Virtnic")
    submit_label = _("Create Virtnic")
    submit_url = reverse_lazy("horizon:network:virtnic:create")

class BindingView(forms.ModalFormView):
    form_class = project_forms.BindingForm
    form_id = "binding_virtnic_form"
    modal_header = _("Binding Virtnic")
    template_name = 'network/virtnic/binding.html'
    success_url = reverse_lazy("horizon:network:virtnic:index")
    page_title = _("Binding Virtnic")
    submit_label = _("Binding")
    submit_url = "horizon:network:virtnic:binding"

    def get_context_data(self, **kwargs):
        context = super(BindingView, self).get_context_data(**kwargs)
        args = (self.kwargs['port_id'],)
        context["port_id"] = self.kwargs['port_id']
        context['submit_url'] = reverse(self.submit_url, args=args)
        return context

    def _get_object(self, *args, **kwargs):
        port_id = self.kwargs['port_id']
        try:
            return api.neutron.port_get(self.request, port_id)
        except Exception:
            redirect = self.success_url
            msg = _('Unable to retrieve router details.')
            exceptions.handle(self.request, msg, redirect=redirect)

    def get_initial(self):
        port = self._get_object()
        initial = {'port_id': port['id'],
                   'name': port['name']}
        return initial


class DetailView(tabs.TabView):
    tab_group_class = project_tabs.VirtnicDetailTabs
    template_name = 'network/virtnic/detail.html'
    page_title = _("Virtnic Details")

    def get_context_data(self, **kwargs):
        context = super(DetailView, self).get_context_data(**kwargs)
        port = self.get_data()
        table = project_tables.VirtnicTable(self.request)
        context["port"] = port
        context["url"] = self.get_redirect_url()
        context["actions"] = table.render_row_actions(port)
        return context

    @staticmethod
    def get_redirect_url():
        return reverse_lazy('horizon:network:virtnic:index')

    @memoized.memoized_method
    def get_data(self):
        try:
            return api.neutron.port_get(self.request, self.kwargs['port_id'])
        except Exception:
            exceptions.handle(self.request,
                              _('Unable to retrieve image details.'),
                              redirect=self.get_redirect_url())

    def get_tabs(self, request, *args, **kwargs):
        port = self.get_data()
        return self.tab_group_class(request, port=port, **kwargs)
