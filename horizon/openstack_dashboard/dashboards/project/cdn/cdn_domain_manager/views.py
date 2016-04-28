# -*- coding: utf-8 -*-
'''
Created on 2015-06-05

@author: yanjj@syscloud.cn
'''

from horizon import exceptions
from horizon import tables
from horizon import forms
from horizon.utils import memoized
from django.core.urlresolvers import reverse
from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext_lazy as _
from openstack_dashboard.dashboards.project.cdn.cdn_domain_manager.models\
    import Domain, SourceAddress, CacheRule, AccessControl
from openstack_dashboard.dashboards.project.cdn.cdn_domain_manager\
    import tables as domain_tables
from openstack_dashboard.dashboards.project.cdn.cdn_domain_manager\
    import forms as domain_forms
from horizon import messages
from openstack_dashboard.dashboards.project.cdn import middware
from django.http import HttpResponseRedirect
import memcache
from django.conf import settings
import logging


class IndexView(tables.DataTableView):
    # cdn domain list view
    table_class = domain_tables.DomainManagerTable
    template_name = 'cdn/cdn.cdn_domain_manager/index.html'

    def _get_domain(self):
        try:
            tenant_id = self.request.user.tenant_id
            domain_list = Domain.objects.filter(tenant_id=tenant_id).exclude(status='deleted')
        except Exception:
            domain_list = []
            exceptions.handle(self.request,
                              _('Unable to retrieve domain name list.'))
        return domain_list

    def get_data(self):
        domains = self._get_domain()
        return domains


class CreateView(forms.ModalFormView):
    ''' create domain '''
    form_class = domain_forms.CreateForm
    form_id = "create_domain_form"
    modal_header = _("Create Domain Name")
    template_name = 'cdn/cdn.cdn_domain_manager/create.html'
    success_url = reverse_lazy("horizon:cdn:cdn.cdn_domain_manager:index")
    page_title = _("Create Domain Name")
    submit_label = _("create")
    submit_url = reverse_lazy("horizon:cdn:cdn.cdn_domain_manager:create")

    def get_context_data(self, **kwargs):
        context = super(CreateView, self).get_context_data(**kwargs)
        context['message'] = _("for example a.test.com or www.test.com,"
                               "please enter under more than one origin config")
        return context


class VerifyView(forms.ModalFormView):
    '''验证域名所有权 '''
    form_class = domain_forms.VerifyForm
    form_id = "verify_domain_form"
    modal_header = _("Verify Domain")
    template_name = 'cdn/cdn.cdn_domain_manager/verify.html'
    success_url = reverse_lazy("horizon:cdn:cdn.cdn_domain_manager:index")
    page_title = _("Verify Domain")
    submit_url = "horizon:cdn:cdn.cdn_domain_manager:action"
    submit_label = _("Verify")

    def get_context_data(self, **kwargs):
        context = super(VerifyView, self).get_context_data(**kwargs)
        domain_id = self.kwargs['domain_id']
        domain = Domain.objects.get(pk=domain_id)
        domain_name = domain.domain_name
        check_method = middware.DomainManage()
        check_info = check_method.verify_file_check(str(domain_name))
        memcached_servers=settings.CACHES.get("default").get("LOCATION")
        mc = memcache.Client(memcached_servers)
        domain_uuid = mc.get(str(domain_name))
        if domain.status == 'unverified' or domain.status == 'failed':
            if domain_uuid is not None:
                if not check_info:
                    context["message"] = _("Please create name which name is on below into your web server(%s),"
                                           "and write: ") % domain_name
                    context["uuid"] = domain_uuid
                    context["file"] = domain_uuid+'.txt'
                    msg = _("Not detected verification file")
                    messages.warning(self.request, msg)
                else:
                    context["message"] = _("Verification file has been detected, please verify")
            else:
                domain.status = 'failed'
                domain.save()
        else:
            context["disable"] = 'disabled="disable"'
            context["message"] = _("The %s status is %s") % (domain.domain_name, _(domain.status))
        args = (self.kwargs['domain_id'],)
        context['submit_url'] = reverse(self.submit_url, args=args)
        return context


class UpdateTabView(tables.MultiTableView):
    '''Edit domain '''
    table_classes = (domain_tables.UpdateAccessControlTable, domain_tables.UpdateCacheRuleTable)
    template_name = 'cdn/cdn.cdn_domain_manager/detail.html'
    failure_url = 'horizon:cdn:cdn.cdn_domain_manager:index'
    modify_url = 'horizon:cdn:cdn.cdn_domain_manager:modify'
    page_title = _("Update Domain Config")

    @memoized.memoized_method
    def _get_data(self):
        try:
            domain_id = self.kwargs['domain_id']
            domain = Domain.objects.get(pk=domain_id)
            source_address = domain.sourceaddress_set.filter(domain_id=domain_id)
            source = [i.source_address for i in source_address]
            domain_class = middware.DomainInfo(domain_name=domain.domain_name, source_type=domain.source_type,
                                               cname=domain.domain_cname, source_address=source,
                                               status=_(domain.status), created_at=domain.created_at)
            return domain_class
        except Exception:
            msg = _('Unable to retrieve details for %s') \
                % domain.domain_name
            exceptions.handle(self.request, msg, redirect=self.failure_url)
        return []

    def get_access_data(self):
        try:
            domain_id = self.kwargs['domain_id']
            domain = Domain.objects.get(pk=domain_id)
            return domain.accesscontrol_set.all()
        except Exception:
            domain_id = self.kwargs['domain_id']
            domain = Domain.objects.get(pk=domain_id)
            msg = _('Unable to retrieve details for "%s".') \
                % domain.domain_name
            exceptions.handle(self.request, msg, redirect=self.failure_url)

    def get_cache_data(self):
        try:
            domain_id = self.kwargs['domain_id']
            domain = Domain.objects.get(pk=domain_id)
            return domain.cacherule_set.all()
        except Exception:
            domain_id = self.kwargs['domain_id']
            domain = Domain.objects.get(pk=domain_id)
            msg = _('Unable to retrieve details for %s') \
                % domain.domain_name
            exceptions.handle(self.request, msg, redirect=self.failure_url)

    def get_context_data(self, **kwargs):
        context = super(UpdateTabView, self).get_context_data(**kwargs)
        domain = self._get_data()
        context["domain"] = domain
        args = (self.kwargs['domain_id'],)
        context["modify_url"] = reverse(self.modify_url, args=args)
        return context


class UpdateDomainFormView(forms.ModalFormView):
    form_class = domain_forms.ModifyDomain
    form_id = "update_domain_form"
    template_name = 'cdn/cdn.cdn_domain_manager/create.html'
    submit_url = 'horizon:cdn:cdn.cdn_domain_manager:modify'
    success_url = 'horizon:cdn:cdn.cdn_domain_manager:update'
    failure_url = 'horizon:cdn:cdn.cdn_domain_manager:update'
    page_title = _("Domadin Info")
    modal_header = _("Update Domain")
    submit_label = _("update")

    def get_submit_url(self):
        return reverse(self.submit_url,
                       args=(self.kwargs['domain_id'],))

    def get_success_url(self):
        return reverse(self.success_url,
                       args=(self.kwargs['domain_id'],))

    def get_object(self):
        try:
            domain_id = self.kwargs["domain_id"]
            return Domain.objects.get(pk=domain_id)
        except Exception:
            redirect = reverse(self.failure_url, args=[domain_id])
            msg = _("Unable to retrieve Domain.")
            exceptions.handle(self.request, msg, redirect=redirect)

    def get_context_data(self, **kwargs):
        context = super(UpdateDomainFormView, self).get_context_data(**kwargs)
        context['message'] = _("Modify Domain origin config,please wrap under more than one origin config")
        context['submit_url'] = self.get_submit_url()
        return context

    def get_initial(self):
        domain = self.get_object()
        origin_address = domain.sourceaddress_set.filter(domain_id=self.kwargs['domain_id'])
        if domain.source_type == 'url':
            a = "origin_config_b"
        else:
            a = "origin_config_a"
        return {"domain_name": domain.domain_name,
                "source_type": domain.source_type,
                a: '\n'.join([i.source_address for i in origin_address])}

    def form_valid(self, form):
        try:
            handled = form.handle(self.request, form.cleaned_data)
        except Exception:
            handled = None
            exceptions.handle(self.request)

        if handled:
            domain_id = self.kwargs["domain_id"]
            source_type = form.cleaned_data["source_type"]
            domain = Domain.objects.get(pk=domain_id)
            domain.source_type = source_type
            origin_address = SourceAddress.objects.filter(domain_id=domain_id)
            if source_type == 'ip':
                source_address = form.cleaned_data["origin_config_a"]
                origin_address.delete()
                clear_list = source_address.strip('\r\n').split('\r\n')
                for i in clear_list:
                    origin_address.create(domain_id=domain_id, source_address=i)
                origin_config = middware.domainApi.OriginConfig(originIps=source_address.split('\r\n'))
            else:
                source_address = form.cleaned_data["origin_config_b"]
                origin_address.delete()
                origin_address.create(domain_id=domain_id, source_address=source_address)
                origin_config = middware.domainApi.OriginConfig(originDomainName=source_address)
            domain.save()
            if domain.domain_id is not None:
                domain_class = middware.domainApi.Domain(domainId=domain.domain_id,
                                                         originConfig=origin_config)
                modify = middware.DomainManage()
                ret = modify.modify(domain_class)
                if ret.getMsg() == 'success':
                    msg = _("modify successfully")
                    messages.success(self.request, msg)
                else:
                    msg = _("modify failed")
                    messages.error(self.request, msg)
                redirect_url = self.get_success_url()
                return HttpResponseRedirect(redirect_url)
            else:
                msg = _("modify successfully")
                redirect_url = self.get_success_url()
                messages.success(self.request, msg)
                return HttpResponseRedirect(redirect_url)
        else:
            return self.form_invalid(form)


class AddAccessFormView(forms.ModalFormView):
    form_class = domain_forms.CreateAccess
    form_id = "create_access_form"
    template_name = 'cdn/cdn.cdn_domain_manager/create.html'
    success_url = 'horizon:cdn:cdn.cdn_domain_manager:update'
    page_title = _("Access Control")
    modal_header = _("Create Domain Access Rule")
    submit_label = _("create")
    submit_url = 'horizon:cdn:cdn.cdn_domain_manager:addaccess'

    def get_success_url(self):
        return reverse(self.success_url,
                       args=(self.kwargs['domain_id'],))

    def get_submit_url(self):
        return reverse(self.submit_url,
                       args=(self.kwargs['domain_id'],))

    def get_context_data(self, **kwargs):
        context = super(AddAccessFormView, self).get_context_data(**kwargs)
        context['message'] = _("Please use enter to split white list,black list,forbid ip")
        context['submit_url'] = self.get_submit_url()
        return context

    def form_valid(self, form):
        try:
            handled = form.handle(self.request, form.cleaned_data)
        except Exception:
            handled = None
            exceptions.handle(self.request)

        if handled:
            domain_id = self.kwargs["domain_id"]
            access_type = form.cleaned_data["type"]
            control_type = form.cleaned_data['access_type']
            refer = form.cleaned_data["refer"]
            white_list = form.cleaned_data["white_list"]
            black_list = form.cleaned_data["black_list"]
            forbid_ip = form.cleaned_data["forbid_ip"]
            domain = Domain.objects.get(pk=domain_id)
            if domain.status == 'Deployed':
                modify = middware.DomainManage()
                if control_type == u'white':
                    if forbid_ip == u'':
                        visitControlRule = middware.domainApi.VisitControlRule(pathPattern=str(access_type),
                                                                               allowNullReferer=refer,
                                                                               validReferers=str(white_list).strip('\r\n').split('\r\n'))
                    else:
                        visitControlRule = middware.domainApi.VisitControlRule(pathPattern=str(access_type),
                                                                               allowNullReferer=refer,
                                                                               validReferers=str(white_list).strip('\r\n').split('\r\n'),
                                                                               forbiddenIps=str(forbid_ip).strip('\r\n').split('\r\n'))
                else:
                    if forbid_ip == u'':
                        visitControlRule = middware.domainApi.VisitControlRule(pathPattern=str(access_type),
                                                                               invalidReferers=str(black_list).strip('\r\n').split('\r\n'))

                    else:
                        visitControlRule = middware.domainApi.VisitControlRule(pathPattern=str(access_type),
                                                                               invalidReferers=str(black_list).strip('\r\n').split('\r\n'),
                                                                               forbiddenIps=str(forbid_ip).strip('\r\n').split('\r\n'))

                domain_class = middware.domainApi.Domain(domainId=domain.domain_id,
                                                         visitControlRules=[visitControlRule])
                ret = modify.modify(domain_class)
                if ret.getMsg() == 'success':
                    msg = _("add successfully")
                    messages.success(self.request, msg)
                    p = domain.accesscontrol_set.create(pathPattern=access_type, allowNullReffer=refer,
                                                        validRefers=white_list, invalidRefers=black_list,
                                                        forbiddenIps=forbid_ip)
                    p.save()
                else:
                    messages.error(self.request, ret.getMsg())
                redirect_url = self.get_success_url()
                return HttpResponseRedirect(redirect_url)
            else:
                msg = _("%s status is %s, can not do this action") % (domain.domain_name, _(domain.status))
                messages.warning(self.request, msg)
                redirect_url = self.get_success_url()
                return HttpResponseRedirect(redirect_url)


class ModifyAccessFormView(forms.ModalFormView):
    form_class = domain_forms.ModifyAccess
    form_id = "modify_access_form"
    template_name = 'cdn/cdn.cdn_domain_manager/create.html'
    success_url = 'horizon:cdn:cdn.cdn_domain_manager:update'
    page_title = _("Access Control")
    modal_header = _("Modify Domain Access Rule")
    submit_label = _("update")
    submit_url = 'horizon:cdn:cdn.cdn_domain_manager:modifyaccess'

    def get_success_url(self):
        return reverse(self.success_url,
                       args=(self.kwargs['domain_id'],))

    def get_submit_url(self):
        return reverse(self.submit_url,
                       args=(self.kwargs['domain_id'], self.kwargs['access_id']))

    def get_context_data(self, **kwargs):
        context = super(ModifyAccessFormView, self).get_context_data(**kwargs)
        context['message'] = _("Modify Domain Access Control")
        context['submit_url'] = self.get_submit_url()
        return context

    def get_initial(self):
        access_id = self.kwargs["access_id"]
        access = AccessControl.objects.get(pk=access_id)
        return {"type": access.pathPattern,
                        "refer": access.allowNullReffer,
                        "black_list": access.invalidRefers,
                        "white_list": access.validRefers,
                        "forbid_ip": access.forbiddenIps}

    def form_valid(self, form):
        try:
            handled = form.handle(self.request, form.cleaned_data)
        except Exception:
            handled = None
            exceptions.handle(self.request)
        if handled:
            domain_id = self.kwargs["domain_id"]
            access_type = form.cleaned_data["type"]
            control_type = form.cleaned_data['access_type']
            refer = form.cleaned_data["refer"]
            white_list = form.cleaned_data["white_list"]
            black_list = form.cleaned_data["black_list"]
            forbid_ip = form.cleaned_data["forbid_ip"]
            domain = Domain.objects.get(pk=domain_id)
            if domain.status == 'Deployed':
                modify = middware.DomainManage()
                if control_type == 'white':
                    if forbid_ip == u'':
                        visitControlRule = middware.domainApi.VisitControlRule(pathPattern=str(access_type),
                                                                               allowNullReferer=refer,
                                                                               validReferers=str(white_list).strip('\r\n').split('\r\n'))
                    else:
                        visitControlRule = middware.domainApi.VisitControlRule(pathPattern=str(access_type),
                                                                               allowNullReferer=refer,
                                                                               validReferers=str(white_list).strip('\r\n').split('\r\n'),
                                                                               forbiddenIps=str(forbid_ip).strip('\r\n').split('\r\n'))
                else:
                    if forbid_ip == u'':
                        visitControlRule = middware.domainApi.VisitControlRule(pathPattern=str(access_type),
                                                                               invalidReferers=str(black_list).strip('\r\n').split('\r\n'))

                    else:
                        visitControlRule = middware.domainApi.VisitControlRule(pathPattern=str(access_type),
                                                                               invalidReferers=str(black_list).strip('\r\n').split('\r\n'),
                                                                               forbiddenIps=str(forbid_ip).strip('\r\n').split('\r\n'))
                domain_class = middware.domainApi.Domain(domainId=domain.domain_id,
                                                         visitControlRules=[visitControlRule])
                ret = modify.modify(domain_class)
                if ret.getMsg() == 'success':
                    msg = _("modify successfully")
                    messages.success(self.request, msg)
                    access_id = self.kwargs['access_id']
                    access = AccessControl.objects.get(pk=access_id)
                    access.pathPattern = access_type
                    access.allowNullReffer = refer
                    access.validRefers = white_list
                    access.invalidRefers = black_list
                    access.forbiddenIps = forbid_ip
                    access.save()
                else:
                    messages.error(self.request, ret.getMsg())
                redirect_url = self.get_success_url()
                return HttpResponseRedirect(redirect_url)

            else:
                msg = _("%s status is %s, can not do this action") % (domain.domain_name, _(domain.status))
                messages.warning(self.request, msg)
                redirect_url = self.get_success_url()
                return HttpResponseRedirect(redirect_url)


class AddCacheFormView(forms.ModalFormView):
    form_class = domain_forms.CreateCache
    form_id = "create_cache_form"
    template_name = 'cdn/cdn.cdn_domain_manager/create.html'
    success_url = 'horizon:cdn:cdn.cdn_domain_manager:update'
    page_title = _("Cache Rule")
    modal_header = _("Create Domain Cache Rule")
    submit_label = _("create")
    submit_url = "horizon:cdn:cdn.cdn_domain_manager:addcache"

    def get_success_url(self):
        return reverse(self.success_url,
                       args=(self.kwargs['domain_id'],))

    def get_submit_url(self):
        return reverse(self.submit_url,
                       args=(self.kwargs['domain_id'],))

    def get_context_data(self, **kwargs):
        context = super(AddCacheFormView, self).get_context_data(**kwargs)
        context['message'] = _("For example: /(a|b)/*.(jpg|bmp|png|gif)")
        context['submit_url'] = self.get_submit_url()
        return context

    def form_valid(self, form):
        try:
            handled = form.handle(self.request, form.cleaned_data)
        except Exception:
            handled = None
            exceptions.handle(self.request)
        if handled:
            domain_id = self.kwargs['domain_id']
            cache_type = form.cleaned_data['type']
            ignore = form.cleaned_data["ignore"]
            time = form.cleaned_data["time"]
            domain = Domain.objects.get(pk=domain_id)
            if domain.status == 'Deployed':
                modify = middware.DomainManage()
                ret = modify.find(domain.domain_id)
                domain_result = ret.getDomain()
                cacheBehavior = middware.domainApi.CacheBehavior(pathPattern=cache_type, ignoreCacheControl=ignore,
                                                                 cacheTtl=time)
                if domain_result.cacheBehaviors is not None:
                    domain_class = middware.domainApi.Domain(domainId=domain.domain_id,
                                                             cacheBehaviors=domain_result.cacheBehaviors+[cacheBehavior])
                else:
                    domain_class = middware.domainApi.Domain(domainId=domain.domain_id, cacheBehaviors=[cacheBehavior])
                ret = modify.modify(domain_class)
                if ret.getMsg() == 'success':
                    msg = _("add successfully")
                    messages.success(self.request, msg)
                    p = domain.cacherule_set.create(pathPattern=cache_type, ignoreCacheControl=ignore, cacheTtl=time)
                    p.save()
                else:
                    messages.error(self.request, ret.getMsg())
                redirect_url = self.get_success_url()
                return HttpResponseRedirect(redirect_url)
            else:
                msg = _("%s status is %s, can not do this action") % (domain.domain_name, _(domain.status))
                messages.warning(self.request, msg)
                redirect_url = self.get_success_url()
                return HttpResponseRedirect(redirect_url)


class ModifyCacheFormView(forms.ModalFormView):
    form_class = domain_forms.ModifyCache
    form_id = "modify_cache_form"
    template_name = 'cdn/cdn.cdn_domain_manager/create.html'
    success_url = 'horizon:cdn:cdn.cdn_domain_manager:update'
    page_title = _("Cache Rule")
    modal_header = _("Modify Domain Cache Rule")
    submit_label = _("update")
    submit_url = "horizon:cdn:cdn.cdn_domain_manager:modifycache"

    def get_success_url(self):
        return reverse(self.success_url,
                       args=(self.kwargs['domain_id'],))

    def get_submit_url(self):
        return reverse(self.submit_url,
                       args=(self.kwargs['domain_id'], self.kwargs['cache_id']))

    def get_context_data(self, **kwargs):
        context = super(ModifyCacheFormView, self).get_context_data(**kwargs)
        context['message'] = _("Modify Domain Cache Rule")
        context['submit_url'] = self.get_submit_url()
        return context

    def get_initial(self):
        cache_id = self.kwargs['cache_id']
        cache = CacheRule.objects.get(pk=cache_id)
        return {"type": cache.pathPattern,
                "ignore": cache.ignoreCacheControl,
                "time": cache.cacheTtl}

    def form_valid(self, form):
        try:
            handled = form.handle(self.request, form.cleaned_data)
        except Exception:
            handled = None
            exceptions.handle(self.request)
        if handled:
            domain_id = self.kwargs['domain_id']
            cache_type = form.cleaned_data['type']
            ignore = form.cleaned_data["ignore"]
            time = form.cleaned_data["time"]
            domain = Domain.objects.get(pk=domain_id)
            if domain.status == 'Deployed':
                modify = middware.DomainManage()
                ret = modify.find(domain.domain_id)
                domain_result = ret.getDomain()
                cacheBehavior = middware.domainApi.CacheBehavior(pathPattern=cache_type, ignoreCacheControl=ignore,
                                                                 cacheTtl=time)
                if domain_result.cacheBehaviors is not None:
                    domain_class = middware.domainApi.Domain(domainId=domain.domain_id,
                                                             cacheBehaviors=domain_result.cacheBehaviors+[cacheBehavior])
                else:
                    domain_class = middware.domainApi.Domain(domainId=domain.domain_id, cacheBehaviors=[cacheBehavior])
                ret = modify.modify(domain_class)
                if ret.getMsg() == 'success':
                    msg = _("modify successfully")
                    messages.success(self.request, msg)
                    cache_id = self.kwargs["cache_id"]
                    cache = CacheRule.objects.get(pk=cache_id)
                    cache.pathPattern = cache_type
                    cache.ignoreCacheControl = ignore
                    cache.cacheTtl = time
                    cache.save()
                else:
                    messages.error(self.request, ret.getMsg())
                redirect_url = self.get_success_url()
                return HttpResponseRedirect(redirect_url)
            else:
                msg = _("%s status is %s, can not do this action") % (domain.domain_name, _(domain.status))
                messages.warning(self.request, msg)
                redirect_url = self.get_success_url()
                return HttpResponseRedirect(redirect_url)


def verify_view(request, domain_id):
    redirect_url = reverse_lazy('horizon:cdn:cdn.cdn_domain_manager:index')
    try:
        domain_id = domain_id
        domain_list = Domain.objects.get(pk=domain_id)
        domain_name = domain_list.domain_name
        origin_type = domain_list.source_type
        origin_address = domain_list.sourceaddress_set.filter(domain_id=domain_id)
        if origin_type == 'url':
            origin_config = middware.domainApi.OriginConfig(originDomainName=origin_address[0].source_address)
        else:
            originips = [i.source_address for i in origin_address]
            origin_config = middware.domainApi.OriginConfig(originIps=originips)
        domain_class = middware.domainApi.Domain(domainName=domain_name, comment='syscloud',
                                                 originConfig=origin_config, serviceType='web')
        domain = middware.DomainManage()
        if domain_list.status == 'unverified' or domain_list.status == 'failed':
            if domain.verify_file_check(str(domain_name)):
                ret = domain.add(domain_class)
                msg = ret.getMsg()
                status = ret.getRet()
                if status == 202:
                    domain_list.status = 'inProgress'
                    domain_list.save()
                    messages.success(request, msg)
                else:
                    messages.error(request, msg)
                    logging.warning('CDN:'+domain_name+':'+msg)
                    domain_list.error_log = msg
                    domain_list.status = 'addfailed'
                    domain_list.save()
            else:
                domain_list.status = 'failed'
                domain_list.save()
        elif domain_list.status == 'addfailed':
            msg = _("Please check the domain config")
            messages.warning(request, msg)
        else:
            msg = _("the %s status is %s") % (domain_list.domain_name, _(domain_list.status))
            messages.warning(request, msg)
        return HttpResponseRedirect(redirect_url)
    except Exception:
        msg = _('Failed')
        redirect = redirect_url
        exceptions.handle(request, msg, redirect=redirect)
        return False

