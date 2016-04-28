# -*- coding: utf-8 -*-
# author__ = 'yanjiajia'

import logging
from horizon import exceptions
from horizon import forms
from horizon import messages
from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext_lazy as _
from openstack_dashboard.dashboards.cdn.cdn_domain_manager.models import Domain, CdnBillMethod
import uuid
import datetime
import calendar
from openstack_dashboard.dashboards.cdn.middware import DomainManage
from openstack_dashboard import api
from openstack_dashboard.utils.memcache_manager import set_memcache_value


level_choice = [
    ('ip', _("Origin IP")),
    ('url', _("Origin Domain Name"))]
LOG = logging.getLogger(__name__)

access_choice = [
    ('white', _("White List")),
    ('black', _('Black List'))
]


class CreateForm(forms.SelfHandlingForm):
    '''创建加速域名自处理modal表单'''
    domain_name = forms.CharField(max_length=64, label=_("Domain Name"), required=True)
    source_type = forms.ChoiceField(label=_("Origin Domain Type"),
                                    choices=level_choice,
                                    widget=forms.Select(attrs={'class': 'switchable',
                                                                    'data-slug': 'origintype'},),
                                    required=True)
    origin_config_a = forms.CharField(label=_("IP Address"),
                                      widget=forms.Textarea(attrs={'class': 'switched',
                                                                        'data-switch-on': 'origintype',
                                                                        'data-origintype-ip': _("IP Address List"),
                                                                        }),
                                      required=False)
    origin_config_b = forms.CharField(max_length=64, label=_("Origin Domain Name"),
                                      widget=forms.TextInput(attrs={'class': 'switched',
                                                                  'data-switch-on': 'origintype',
                                                                  'data-origintype-url': _("Origin Domain Name"),
                                                                   }),
                                      required=False)
    failure_url = 'horizon:cdn:cdn_domain_manager:index'

    def __init__(self, request, *args, **kwargs):
        super(CreateForm, self).__init__(request, *args, **kwargs)

    def handle(self, request, data):
        try:
            tenant_id = self.request.user.tenant_id
            user_name = self.request.user.username
            project_name = self.request.user.project_name
            domain = Domain.objects.filter(domain_name=data['domain_name'])
            # 判断域名是否已添加
            if domain:
                if domain[0].status != 'deleted':
                    message = _('%s has created') % data['domain_name']
                    messages.warning(request, message)
                    return True

                if domain[0].status == 'deleted':
                    domainId=domain[0].domain_id
                    domain_api = DomainManage()
                    domain_api.enable(domainId=domainId)
                    domain[0].status = 'inProgress'
                    domain[0].save()
                    message = _('%s has been in database,it will be enable for you') % data['domain_name']
                    messages.success(request, message)
                    return True

            else:
                # 添加记费类型
                billing_type = CdnBillMethod.objects.get(tenant_id=tenant_id)
                domain_name = data['domain_name'].strip()
                p = Domain(tenant_id=tenant_id, user_name=user_name, project_name=project_name,
                           domain_name=domain_name, domain_cname='-', source_type=data['source_type'],
                           current_type=billing_type.current_type,update_type=billing_type.update_type,
                           update_at=billing_type.update_at,effect_at=billing_type.effect_at)
                p.save()
                if data['source_type'] == 'ip':
                    for i in data['origin_config_a'].strip('\r\n').split('\r\n'):
                        o = p.sourceaddress_set.create(source_address=i)
                        o.save()
                else:
                    o = p.sourceaddress_set.create(source_address=data['origin_config_b'])
                    o.save()

                # 插入操作日志
                api.logger.Logger(self.request).create(resource_type='CDN', action_name='Create Domain Name',
                                                       resource_name='CDN', config=_('Domain: %s') %data['domain_name'],
                                                       status='Success')

                # 将domain_name和随机生成的uuid绑定存储到memcache中，为域名鉴权提供依据
                set_memcache_value(str(data['domain_name']), str(uuid.uuid4()))
                message = _('Domain %s was successfully created') % data['domain_name']
                messages.success(request, message)
                return data['domain_name']
        except exceptions:

            # 插入操作日志
            api.logger.Logger(self.request).create(resource_type='CDN', action_name='Create Domain Name',
                                                       resource_name='CDN', config=_('Domain: %s') %data['domain_name'],
                                                       status='Error')


            msg = _('Failed to create Domain %s') % data['name']
            redirect = self.failure_url
            exceptions.handle(request, msg, redirect=redirect)
            return False


class VerifyForm(forms.SelfHandlingForm):
    redirect_url = reverse_lazy('horizon:cdn:cdn_domain_manager:index')

    def __init__(self, request, *args, **kwargs):
        super(VerifyForm, self).__init__(request, *args, **kwargs)

    def handle(self, request, data):
        return True


class ModifyDomain(CreateForm):
    domain_name = forms.CharField(max_length=64, label=_("Domain Name"), required=True,
                                  widget=forms.TextInput(attrs={'readonly': 'readonly'}))

    def __init__(self, request, *args, **kwargs):
        super(ModifyDomain, self).__init__(request, *args, **kwargs)

    def handle(self, request, data):
        return True


class CreateAccess(forms.SelfHandlingForm):
    failure_url = 'horizon:cdn:cdn_domain_manager:update'
    type = forms.CharField(max_length=255, label=_("Type"), required=True)
    access_type = forms.ChoiceField(label=_("Access Type"),
                                    choices=access_choice,
                                    widget=forms.Select(attrs={'class': 'switchable',
                                                                    'data-slug': 'accesstype'},),
                                    required=True)
    refer = forms.BooleanField(label=_("refer"), required=False)
    black_list = forms.CharField(label=_("Black List"), widget=forms.Textarea(attrs={'class': 'switched',
                                                                                     'data-switch-on': 'accesstype',
                                                                                     'data-accesstype-black': _("Black List"),
                                                                                     }), required=False)
    white_list = forms.CharField(label=_("White List"), widget=forms.Textarea(attrs={'class': 'switched',
                                                                                     'data-switch-on': 'accesstype',
                                                                                     'data-accesstype-white': _("White List"),
                                                                                     }), required=False)
    forbid_ip = forms.CharField(label=_("Forbid IP"), widget=forms.Textarea(), required=False)

    def handle(self, request, data):
        return True


class ModifyAccess(CreateAccess):

    def __init__(self, request, *args, **kwargs):
        super(ModifyAccess, self).__init__(request, *args, **kwargs)

    def handle(self, request, data):
        return True


class CreateCache(forms.SelfHandlingForm):
    failure_url = 'horizon:cdn:cdn_domain_manager:update'
    type = forms.CharField(max_length=255, label=_("Type"))
    ignore = forms.BooleanField(label=_("ignore"), required=False)
    time = forms.IntegerField(label=_("Time"))

    def handle(self, request, data):
        return True


class ModifyCache(CreateCache):

    def __init__(self, request, *args, **kwargs):
        super(ModifyCache, self).__init__(request, *args, **kwargs)

    def handle(self, request, data):
        return True


class ModifyAccountModeForm(forms.SelfHandlingForm):
    failure_url = 'horizon:cdn:cdn_domain_manager:index'
    account_mode = forms.ChoiceField(label=_("Account Mode"), choices=(('cdnflow', _("Flow Account")),(
                                                                        'cdnbandwidth',_('Bandwidth Account'))))

    def handle(self, request, data):
        try:
            now_date = datetime.datetime.utcnow()
            days = calendar.monthrange(now_date.year,now_date.month)[1]
            effect_date = (datetime.date.today().replace(day=1) + datetime.timedelta(days)).replace(day=1)
            tenant_id = self.request.user.tenant_id
            billing_type = CdnBillMethod.objects.get(tenant_id=tenant_id)
            update_type = billing_type.update_type
            post_type = data.get('account_mode')
            if post_type != update_type:
                domain_list = Domain.objects.filter(tenant_id=tenant_id)
                for i in domain_list:
                    i.update_type = post_type
                    i.update_at = now_date
                    i.effect_at = effect_date
                    i.save()
                # change billing method
                billing_type.update_type = post_type
                billing_type.update_at = now_date
                billing_type.effect_at = effect_date
                billing_type.save()
                message = _('Modfiy account method successfully')
                messages.success(request, message)
            else:
                message = _('Your account method is same, do not modify')
                messages.success(request, message)
            return True
        except exceptions:
            msg = _('Failed to change account method')
            LOG.info(msg)
            redirect = self.failure_url
            exceptions.handle(request, msg, redirect=redirect)
            return False
