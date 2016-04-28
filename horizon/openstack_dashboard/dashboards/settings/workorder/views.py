__author__ = 'yamin'
from horizon import tables
from openstack_dashboard.dashboards.settings.workorder import tables as workorder_tables
from horizon import exceptions
from django.utils.translation import ugettext_lazy as _
from openstack_dashboard import api
from horizon import messages,views
from  django import forms
from django.http import HttpResponse,HttpResponseRedirect
from horizon.utils import functions as utils
from forms import QueryForm,CreateWorkOrderForm
from horizon import forms
from django.core.urlresolvers import reverse,reverse_lazy

class IndexView(tables.DataTableView):
    table_class = workorder_tables.WorkOrderTable
    template_name = 'settings/workorder/index.html'
    page_title = _("WorkOrder List")

    def __init__(self, *args, **kwargs):
        self.pagination=None
        super(IndexView, self).__init__(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)
        context['form'] = QueryForm()
        context['pagination'] = self.pagination
        context['statics'] = self.statics
        context['unconfirmed'] =str(sum((value for key,value in self.statics.items() if key!="confirmed")))
        context['notice']=_('Notice:you have %s of work order not been confirmed!') % context['unconfirmed']
        return context

    def get_form_params(self):
        req=self.request
        form=QueryForm(req.GET)
        params={}
        params["pageNo"]=req.GET.get('page_no',0)
        params["pageSize"]=utils.get_page_size(req)
        params["apply_start"]=req.GET.get('start',)
        params["apply_end"]=req.GET.get('end',)
        params["status"]=req.GET.get('status','all')
        params["type"]=req.GET.get('type','all')
        params["sno"]=req.GET.get('workorder_no',)
        params["apply_by"]=req.user.username
        params["user"]=req.user.username
        return params

    def get_data(self):
        req=self.request
        try:
            params=self.get_form_params()
            data,pagination,statics=api.billing.BillingWorkOrder(req).get_wordorder_list(params)
            self.statics=statics
            self.pagination=pagination
            return data
        except Exception:
            exceptions.handle(req,_('Unable to retrieve workorder list.'))
            return []

class DetailView(views.HorizonTemplateView):
    '''
    workorder detail
    '''
    template_name = 'settings/workorder/detail.html'
    def get_context_data(self, **kwargs):
        req=self.request
        context = super(DetailView, self).get_context_data(**kwargs)
        context["user"]=req.user.username
        context['workorderno'] = kwargs.get("workorderno")
        data=api.billing.BillingWorkOrder(req).get_workorder_detail({"workorderno":context['workorderno']})
        context['workorder'] = data
        context['workorderrecordlist'] = context["workorder"]["records"] if context["workorder"] else None
        return context

    def get(self, request, *args, **kwargs):
        return super(DetailView,self).get(self, request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        req=self.request
        workorder_status=request.POST.get("status")#workorder,status
        if workorder_status=="confirmed":#can't do anything about a confirmed workorder
            return super(DetailView,self).get(self, request, *args, **kwargs)
        if request.POST.get("submit_respond"):
            info={
                "workorderno":request.POST.get("workorderno"),
                "content":request.POST.get("content"),
                "applier":request.POST.get("user"),
            }
        else:
            info={
                "workorderno":request.POST.get("workorderno"),
                "content":request.POST.get("content"),
                "applier":request.POST.get("user"),
                "status":"confirmed"
            }
        if not info["content"] and not info["status"]:
            return HttpResponse('fail')
        response=api.billing.BillingWorkOrder(req).create_record(info)
        if request.POST.get("submit_respond"):
            return super(DetailView,self).get(self, request, *args, **kwargs)
        else:
            return HttpResponseRedirect (reverse("horizon:settings:workorder:index"))

class CreateWorkOrder(forms.ModalFormView):
    form_class = CreateWorkOrderForm
    form_id = "create_workorder_form"
    modal_header = _("Create Work Order")
    modal_id = "create_workorder_modal"
    page_title = _("Create Work Order")
    submit_label = _("Create Work Order")
    submit_url = reverse_lazy("horizon:settings:workorder:create")
    success_url = 'horizon:settings:workorder:index'
    template_name = 'settings/workorder/create.html'
    def get_success_url(self):
        return reverse(self.success_url,
                       kwargs={})