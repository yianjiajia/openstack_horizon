__author__ = 'yamin'
from horizon import forms
from horizon.utils import validators
from django.forms import ValidationError  # noqa
from openstack_dashboard import api
from django.views.decorators.debug import sensitive_variables
from django.conf import settings
from horizon.utils import functions as utils
from django import http
from horizon import exceptions
from django.utils.translation import ugettext_lazy as _
from horizon import messages

HANDLER_CHOICES = (('all',_('All')),('responsible',_('Person Responsible')),('submitter',_('Person Submit')))
STATUS_CHOICES = (('all',_('All')),('handling',_('Work Order Handling')),('handled',_('Work Order Handled')),('confirmed',_('Work Order Confirmed')),
                  ('delay',_('Work Order Delay')),('apply',_('Work Order Apply')))
TYPE_CHOICES= (('all',_('All')),('consult',_('Work Order Consult')),('function',_('Work Order Function')),('error',_('Work Order Error')),
               ('finance',_('Work Order Finance')),('regionQuota',_('Work Order RegionQuota')),('others',_('Work Order Others')))
TYPE_CHOICES1=(('consult',_('Work Order Consult')),('function',_('Work Order Function')),('error',_('Work Order Error')),
               ('finance',_('Work Order Finance')),('regionQuota',_('Work Order RegionQuota')),('others',_('Work Order Others')))
from horizon.forms.base import DateForm

class QueryForm(DateForm):
    workorder_no = forms.CharField(max_length=128, label=_("Work Order ID"), required=False,initial="")
    status = forms.ChoiceField(label=_('Work Order Status'), required=True, choices=STATUS_CHOICES,initial="all")
    type = forms.ChoiceField(label=_('Work Order Type'), required=True, choices=TYPE_CHOICES,initial="all")
    page_no = forms.CharField(max_length=32, required=False, widget= forms.HiddenInput)
    # date_from=forms.DateField(label=_('Start'), required=False,input_formats=("%Y-%m-%d",))
    # date_to=forms.DateField(label=_('End'), required=False,input_formats=("%Y-%m-%d",))
    # def __init__(self, *args, **kwargs):
    #     super(QueryForm, self).__init__(*args, **kwargs)
    #     self.fields['date_from'].widget.attrs['data-date-format'] = "yyyy-mm-dd"
    #     self.fields['date_to'].widget.attrs['data-date-format'] = "yyyy-mm-dd"

class CreateWorkOrderForm(forms.SelfHandlingForm):
    theme = forms.CharField(label=_("Work Order Theme"),required=True,initial="")
    type = forms.ChoiceField(label=_('Work Order Type'), required=True, choices=TYPE_CHOICES1,initial="consult")
    content = forms.CharField(label=_("Work Order Content"), required=True,widget=forms.Textarea,initial="")
    no_autocomplete = True

    def clean(self):
        '''Check to make sure password fields match.'''
        return super(CreateWorkOrderForm,self).clean()

    # We have to protect the entire "data" dict because it contains the
    # oldpassword and newpassword strings.
    @sensitive_variables('data')
    def handle(self, request, data):
        try:
            data["applier"]=request.user.username
            data["source"]="openstack"
            response=api.billing.BillingWorkOrder(request).create_workorder(data)
            return response
        except Exception as e:
            messages.error(request, _('Create Work Order failed.'))
            return False
