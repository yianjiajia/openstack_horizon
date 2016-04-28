# -*- coding:utf-8 -*-
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
from django.core.context_processors import request

"""
Template tags for customizing Horizon.
"""

from django.conf import settings
from django.core.urlresolvers import reverse
from django import template
from django.utils.translation import ugettext_lazy as _
import hashlib   
try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode 
register = template.Library()

# payment center
class SitePaymentUrlNode(template.Node):
    def render(self, context):
        request=context['request']
        account_id=''
        payment_url=''
        if 'account' in request.session:
            account=request.session['account']
            account_id=account['account_id']
            params={"account":account_id}
            sign=self._generate_md5_sign(params)
            params.update({"sign":sign})
            payment_url=self._generate_payment_url(params)
            
        return payment_url

    def _generate_md5_sign(self,params):
        #md5加密生成签名
        src = '&'.join(['%s=%s' % (key, value) for key,value in sorted(params.items())]) + settings.MD5_KEY
        return hashlib.md5(src.encode('utf-8')).hexdigest()

    def _generate_payment_url(self,params_signed):
        return '%s?%s' % (settings.PAYMENT_URL, urlencode(params_signed))
 

@register.tag
def site_payment_url(parser, token):
    return SitePaymentUrlNode()

class SiteBillingUrlNode(template.Node):
    def render(self, context):
        request=context['request']
        account_id=''
        if 'account' in request.session:
            account=request.session['account']
            account_id=account['account_id']
        str=account_id+settings.MD5_KEY
        return settings.BILLING_CENTER_URL+"?account_id="+account_id+"&sign="+self.getMD5(str)

    def getMD5(self,str):
        m2 = hashlib.md5()   
        m2.update(str)
        return m2.hexdigest()

@register.tag
def site_billing_url(parser, token):
    return SiteBillingUrlNode()

class SiteBrandingNode(template.Node):
    def render(self, context):
        request=context['request']
        host=self.checkHost(request)
        if host:
            return ('@'+host).upper()
        else:
            return getattr(settings, "SITE_BRANDING", _("Horizon"))
    
    def checkHost(self,request):
        host = request.get_host()
        host_list=host.split(':')
        host=host_list[0]
        return host

@register.tag
def site_branding(parser, token):
    return SiteBrandingNode()

class SiteLogoNode(template.Node):
    def render(self, context):
        request=context['request']
        host=self.checkHost(request)
        logo=''
        if host:
            logo=host['logoName']
        return logo
    # check host name   
    def checkHost(self,request):
        host = request.get_host()
        host_list=host.split(':')
        host=host_list[0]
        currentHost=''
        hostmanage=settings.HOSTMANAGE
        if hostmanage.has_key(host):
            currentHost=hostmanage[host]
            logoDic=host.split(".")
            currentHost["logoName"]=logoDic[-2]
        return currentHost
    
@register.tag
def site_logo(parser, token):
    return SiteLogoNode()

class SiteRegisterStatusNode(template.Node):
    def render(self, context):
        request=context['request']
        register=''
        if settings.REGISTER_STATUE is 'ON': 
            status=self.checkHost(request)
            if status is 'ON':
                register='<a href="/register/" class="register seturl">注册</a>｜' 
        return register
    # check host name   
    def checkHost(self,request):
        host = request.get_host()
        host_list=host.split(':')
        host=host_list[0]
        RegisterStatus='ON'
        hostmanage=settings.HOSTMANAGE
        if hostmanage.has_key(host):
            RegisterStatus=hostmanage[host]['regiser_status']
        return RegisterStatus
    
@register.tag
def site_register_status(parser, token):
    return SiteRegisterStatusNode()

@register.tag
def site_title(parser, token):
    return settings.SITE_BRANDING


@register.simple_tag
def site_branding_link():
    return getattr(settings, "SITE_BRANDING_LINK",
                   reverse("horizon:user_home"))



# TODO(jeffjapan): This is just an assignment tag version of the above, replace
#                  when the dashboard is upgraded to a django version that
#                  supports the @assignment_tag decorator syntax instead.
class SaveBrandingNode(template.Node):
    def __init__(self, var_name):
        self.var_name = var_name

    def render(self, context):
        context[self.var_name] = settings.SITE_BRANDING
        return ""


@register.tag
def save_site_branding(parser, token):
    tagname = token.contents.split()
    return SaveBrandingNode(tagname[-1])



