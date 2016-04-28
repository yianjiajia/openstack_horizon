# -*- coding: utf-8 -*-
# author__ = 'yanjiajia'

import logging
from horizon import exceptions
from horizon import forms
from horizon import messages
from django.core.urlresolvers import reverse
from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext_lazy as _
from openstack_dashboard.dashboards.project.cdn.cdn_domain_manager.models import Domain, SourceAddress
from openstack_dashboard.dashboards.project.cdn import middware
import memcache
import uuid
from django.conf import settings

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
    failure_url = 'horizon:cdn:cdn.cdn_domain_manager:index'

    def __init__(self, request, *args, **kwargs):
        super(CreateForm, self).__init__(request, *args, **kwargs)

    def handle(self, request, data):
        try:
            tenant_id = self.request.user.tenant_id
            domain = [i for i in Domain.objects.filter(domain_name=data['domain_name']) if i.status != 'deleted']
            # 判断域名是否已添加
            if domain:
                message = _('Domain %s has created.') % data['domain_name']
                messages.error(request, message)
                return []
            else:
                p = Domain(tenant_id=tenant_id, domain_name=data['domain_name'],
                           domain_cname='-', source_type=data['source_type'])
                p.save()
                if data['source_type'] == 'ip':
                    for i in data['origin_config_a'].strip('\r\n').split('\r\n'):
                        o = p.sourceaddress_set.create(source_address=i)
                        o.save()
                else:
                    o = p.sourceaddress_set.create(source_address=data['origin_config_b'])
                    o.save()
                # 将domain_name和随机生成的uui绑定存储到memcache中，为域名鉴权提供依据
                memcached_servers=settings.CACHES.get("default").get("LOCATION")
                mc = memcache.Client(memcached_servers)
                mc.set(str(data['domain_name']), str(uuid.uuid4()))
                message = _('Domain %s was successfully created') % data['domain_name']
                messages.success(request, message)
                return data['domain_name']
        except exceptions as exc:
            if exc.status_code == 409:
                msg = _('Quota exceeded for resource domain.')
            else:
                msg = _('Failed to create Domain %s') % data['name']
            LOG.info(msg)
            redirect = self.failure_url
            exceptions.handle(request, msg, redirect=redirect)
            return False


class VerifyForm(forms.SelfHandlingForm):
    redirect_url = reverse_lazy('horizon:cdn:cdn.cdn_domain_manager:index')

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
    failure_url = 'horizon:cdn:cdn.cdn_domain_manager:update'
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
    failure_url = 'horizon:cdn:cdn.cdn_domain_manager:update'
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
