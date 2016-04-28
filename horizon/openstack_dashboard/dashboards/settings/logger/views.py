__author__ = 'gaga'
from horizon import tables
from openstack_dashboard.dashboards.settings.logger import tables as logger_tables
from horizon import exceptions
from django.utils.translation import ugettext_lazy as _
from openstack_dashboard import api
from horizon import messages
from  django import forms
from horizon.utils import functions as utils


TYPE_CHOICES = (('all',_('All')),('instance',_('Instance')),('image',_('Image Disk')),('network',_('Network')),
                ('route',_('Route')),('virtnic',_('Virtual Network Card')),('floatip',_('Float IP')),('snapshot', _('Snapshot')),
                ('loadblance',_('Load Blance')),('volume',_('Cloud Hdd')),('cdn',_('CDN')),('vpn',_('VPN')),
                ('firewall',_('Firewall')),('keypair',_('Keypair')),('user', _('User')),('account', _('Account')),
                ('address', _('Invoices Address')),('discount', _('Discount')),('recharge', _('Recharge')),
                ('destroy_all_resources', _('Destroy all resources')))
ADMIN_TYPE_CHOICES = TYPE_CHOICES+('physicalhost',_('Physical Host'))
REGION_CHOICES = (('all',_('All')),('RegionOne',_('RegionOne')),('RegionTwo',_('RegionTwo')), ('RegionThree',_('RegionThree')),
                  ('Billing', _('Billing')))
STATUS_CHOICES = (('all',_('All')),('success',_('Success')),('error',_('Error')))

class QueryForm(forms.Form):
    type = forms.ChoiceField(label=_('Resource'), required=True, choices=TYPE_CHOICES)
    region = forms.ChoiceField(label=_('Region'), required=True, choices=REGION_CHOICES)
    status = forms.ChoiceField(label=_('Status'), required=True, choices=STATUS_CHOICES)
    project_id = forms.CharField(max_length=128, label=_("Project ID"), required=False)
    user_id = forms.CharField(max_length=128, label=_("User ID"), required=False)
    page_no = forms.CharField(max_length=32, required=False, widget= forms.HiddenInput)

class LogBaseUsage(object):
    show_terminated = False

    def __init__(self, request):
        self.request = request
        self.summary = {}
        self.usage_list = {}

    def get_form(self):
        if not hasattr(self, 'type_form'):
            page_size = utils.get_page_size(self.request)
            req = self.request
            type_form = req.GET.get('type', req.session.get('logger_type'))
            region_form = req.GET.get('region', req.session.get('logger_region'))
            status_form = req.GET.get('status', req.session.get('logger_status'))
            project_id = req.GET.get('project_id', req.session.get('logger_project_id'))
            user_id = req.GET.get('user_id', req.session.get('logger_user_id'))
            page_no = req.GET.get('page_no',)
            if type_form and region_form and status_form:
                # init form
                self.form = QueryForm(initial={'type': type_form,'region': region_form,
                                               'status': status_form, 'page_no': page_no, 'project_id': project_id,
                                               'user_id': user_id})
            else:
                self.form = QueryForm()
            req.session['logger_type'] = type_form
            req.session['logger_region'] = region_form
            req.session['logger_status'] = status_form
            req.session['logger_project_id'] = project_id
            req.session['logger_user_id'] = user_id
            return type_form, region_form, status_form, page_size, page_no, project_id, user_id

    def get_usage_list(self, type, region, status, pageSize, pageNo, proejct_id, user_id):
        return {}

    def summarize(self, type, region, status, pageSize, pageNo, proejct_id, user_id):
        try:
            self.usage_list = self.get_usage_list(type, region, status, pageSize, pageNo, proejct_id, user_id)
        except Exception:
            exceptions.handle(self.request,
                                  _('Unable to retrieve usage information.'))


class LogUsage(LogBaseUsage):
    show_terminated = True

    def get_usage_list(self, type, region, status, pageSize, pageNo, proejct_id, user_id):
        try:
            log = api.logger.Logger(self.request)
            log_dict = log.list(**{'type':type,'region':region,'status':status,
                                   'pageSize':pageSize, 'pageNo': pageNo, 'project_id': proejct_id, 'user_id': user_id})
            return log_dict
        except Exception:
            exceptions.handle(self.request,
                              _('Unable to retrieve data'))
            return {}


class IndexView(tables.DataTableView):
    usage_class =  LogUsage
    table_class = logger_tables.LoggerTable
    template_name = 'settings/logger/index.html'
    page_title = _("Log Manager")

    def __init__(self, *args, **kwargs):
        super(IndexView, self).__init__(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)
        role_name = self.request.user.roles[0].get('name')
        if not self.request.user.is_superuser and role_name != 'support':
            del self.table.columns['project_name']
            del self.table.columns['user_name']
            del self.usage.form.fields['project_id']
            del self.usage.form.fields['user_id']
        context['form'] = self.usage.form
        context['pagination'] = self.usage.usage_list.get('pagination')
        return context

    def get_data(self):
        try:
            self.usage = self.usage_class(self.request)
            self.usage.summarize(*self.usage.get_form())
            return self.usage.usage_list.get('data', [])
        except Exception:
            exceptions.handle(self.request,
                              _('Unable to retrieve domain information.'))
            return []






