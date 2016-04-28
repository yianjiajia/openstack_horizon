# -*- coding: utf-8 -*-
'''
Created on 2015-6-16
@author: yanjj@syscloud.cn
@version: 1.0
@功能：
１．加速域名所有权校验
２．加速域名删除确认校验，短信及邮件方式
3 .手机短信验证
'''
from __future__ import division
import urllib2
import sys
from openstack_dashboard.api.cdn.api import domainApi
from openstack_dashboard.api.cdn.api import purgeApi
from openstack_dashboard.api.cdn.api import reportApi
from openstack_dashboard.api.cdn.api import requestApi
from openstack_dashboard.dashboards.cdn.cdn_domain_manager.models import Domain
import re
import datetime
from django.utils import timezone
from horizon import forms
from horizon import messages
from django.utils.translation import ugettext_lazy as _
from horizon import exceptions
from horizon import tables
from openstack_dashboard.utils.memcache_manager import get_memcache_value

sys.path.append("/etc/openstack-dashboard")
sys.path.append("openstack_dashboard/local")
from local_settings import CDN_USER, CDN_API_KEY


class DomainManage(domainApi.DomainApi):
    '''封装cdn api'''
    def __init__(self, user=CDN_USER, apiKey=CDN_API_KEY):
        super(DomainManage, self).__init__(user=user, apiKey=apiKey)

    def _url_check(self, domain):
        result = domain
        if not domain.startswith('http://'):
            result = 'http://'+domain
        return result

    def verify_file_check(self, domain_url):
        '''验证文件是否存在检查'''
        try:
            domain_uuid = get_memcache_value(domain_url)
            uuid_match = re.compile(domain_uuid)
            if domain_uuid is not None:
                url = self._url_check(domain_url)+'/'+domain_uuid+'.txt'
                html = urllib2.urlopen(url)
                uuid = html.read()
                if html.code == 200 and uuid_match.match(uuid):
                    return True
            else:
                return False
        except Exception:
            return False


class PurgeManage(purgeApi.PurgeApi):
    '''封装初始化方法'''
    def __init__(self, user=CDN_USER, apiKey=CDN_API_KEY):
        super(PurgeManage, self).__init__(user=user, apiKey=apiKey)


class RequestManage(requestApi.RequestApi):
    '''封装初始化方法'''
    def __init__(self, user=CDN_USER, apiKey=CDN_API_KEY):
        super(RequestManage, self).__init__(user=user, apiKey=apiKey)


class ReportManage(reportApi.ReportApi):
    '''封装初始化方法'''
    def __init__(self, user=CDN_USER, apiKey=CDN_API_KEY):
        super(ReportManage, self).__init__(user=user, apiKey=apiKey)


class DomainInfo(object):
    '''domainifo 对象封装'''
    def __init__(self, pk=None, domain_name=None, source_type=None, cname=None,
                 source_address=None, status=None, created_at=None):
        """

        :rtype : object
        """
        self.id = pk
        self.domain_name = domain_name
        self.source_type = source_type
        self.domain_cname = cname
        self.source_address = source_address
        self.status = status
        self.created_at = created_at


class DataStatistics(object):
    '''DataStatistics object'''
    def __init__(self, project_id=None, user_name=None, project_name=None, cdn_count=None, total_flow=None,
                 total_requests=None,time_section=None):
        """

        :rtype : object
        """
        self.Project_id = project_id
        self.User_name = user_name
        self.Project_name = project_name
        self.Cdn_count = cdn_count
        self.Total_Flow = total_flow
        self.Total_Requests = total_requests
        self.Time_Section = time_section


class TenantStatistics(object):
    '''TenantStatistics object'''
    def __init__(self, domain=None, month=None, flow=None,
                 requests=None, io=None):
        """

        :rtype : object
        """
        self.domain_name = domain
        self.month = month
        self.flow = flow
        self.requests = requests
        self.io = io


class LogData(object):
    '''TenantStatistics object'''
    def __init__(self, domain=None, log_url=None, size=None,
                 begin=None, end=None):
        """

        :rtype : object
        """
        self.domain_name = domain
        self.log_url = log_url
        self.log_size = size
        self.begin = begin
        self.end = end


class MonData(object):
    '''TenantStatistics object'''
    def __init__(self, date=None, top_io=None, total_flow=None, total_requests=None):
        """

        :rtype : object
        """
        self.date = date
        self.top_io = top_io
        self.total_flow = total_flow
        self.total_requests = total_requests


class PureData(object):
    '''TenantStatistics object'''
    def __init__(self, cache_type=None, cache_time=None, status=None):
        """

        :rtype : object
        """
        self.cache_type = cache_type
        self.cache_time = cache_time
        self.status = _(status)


def get_flow_report(dateFrom, dateTo, tenant_domain_list_dict):
    '''流量统计算法'''
    Flow = 0
    midd = 0
    Kwag1 = {}
    report = ReportManage()
    ReportForm = reportApi.ReportForm(dateFrom=dateFrom, dateTo=dateTo, reportType='daily')
    for k,v in tenant_domain_list_dict.iteritems():
        for p in v:
            ret = report.getFlowReport(ReportForm, p)
            if ret:
                for i in ret:
                    midd += i.flowSummary
            Flow += float(midd)
        Kwag1[k] = Flow
    return Kwag1


def get_hit_report(dateFrom, dateTo, tenant_domain_list_dict):
    '''请求数统计算法'''
    Hit = 0
    midd = []
    domain_hit = 0
    Kwag2 = {}
    report = ReportManage()
    ReportForm = reportApi.ReportForm(dateFrom=dateFrom, dateTo=dateTo, reportType='daily')
    for k,v in tenant_domain_list_dict.iteritems():
        for s in v:
            ret = report.getHitReport(ReportForm, s)
            for i in ret:
                midd += i.getHitPoints()
            if midd:
                for p in midd:
                    domain_hit += int(p.hit)
                Hit += domain_hit
        Kwag2[k] = Hit
    return Kwag2


def get_all_data(dateFrom, dateTo):
    try:
        data = []
        tenant_domain_list_dict = {}
        project_user_name_dict = {}
        data_from_mysql = [i for i in Domain.objects.all() if i.domain_id is not None and i.status != 'deleted']
        tenant_domain_list = [[t.tenant_id, t.domain_id] for t in data_from_mysql]
        project_user_name = [[s.tenant_id, s.project_name, s.user_name] for s in data_from_mysql]
        for p in tenant_domain_list:
            tenant_domain_list_dict[p[0]] = tenant_domain_list_dict.setdefault(p[0], []) + [p[1]]
        for j in project_user_name:
            project_user_name_dict[j[0]] = project_user_name_dict.setdefault(j[0], []) + [(j[1],j[2])]
        hit_ret = get_hit_report(str(dateFrom), str(dateTo), tenant_domain_list_dict)
        flow_ret = get_flow_report(str(dateFrom), str(dateTo), tenant_domain_list_dict)
        for k in hit_ret:
            tenant_cdn_count = len(tenant_domain_list_dict[k])
            project_name, user_name = project_user_name_dict[k][0]
            data.append(DataStatistics(project_id=k, user_name=user_name, project_name=project_name, cdn_count=tenant_cdn_count,
                                       total_flow=flow_ret[k], total_requests=hit_ret[k],
                                       time_section=(dateTo-dateFrom).days))
        return data
    except Exception:
        return []


def get_purge_data(dateFrom, dateTo, tenant_id):
    try:
        data = []
        purge = PurgeManage()
        ret = purge.purgeQuery(dateFrom, dateTo)
        domain_name_list = [j.domain_name for j
                            in Domain.objects.filter(tenant_id=tenant_id) if j.domain_id is not None]
        for i in ret.getPurgeList():
            for p in i.itemList:
                for k in domain_name_list:
                    match = re.search(k, p.url)
                    if match:
                        data.append(PureData(cache_type=p.url, cache_time=i.requestDate, status=p.status))
        return data
    except Exception:
        return []


def get_mon_data(dateFrom, dateTo, domain_id):
    data = []
    flowPoints = []
    hitPoints = []
    report_class = ReportManage()
    ReportForm = reportApi.ReportForm(dateFrom, dateTo, reportType='fiveminutes')
    d_flow = {}
    d_hit = {}
    ret_flow = report_class.getFlowReport(ReportForm, domain_id)
    for g in ret_flow:
        flowPoints += g.getFlowPoints()
    ret_hit = report_class.getHitReport(ReportForm, domain_id)
    for s in ret_hit:
        hitPoints += s.getHitPoints()
    if flowPoints:
        flow_clean_data = [[j.point.strftime("%Y-%m-%d"), float('%0.2f' % (float(j.flow)))] for j in flowPoints]
        for i in flow_clean_data:
            d_flow[i[0]] = d_flow.setdefault(i[0], []) + [i[1]]
    if hitPoints:
        hit_clean_data = [[k.point.strftime("%Y-%m-%d"), int(str(k.hit))] for k in hitPoints]
        for l in hit_clean_data:
            d_hit[l[0]] = d_hit.setdefault(l[0],0) + l[1]
    for k in d_flow:
        io = max(d_flow[k])*8/(5*60)
        flow = sum(d_flow[k])
        requests = d_hit[k]
        data.append(MonData(date=k, top_io=io, total_flow=flow, total_requests=requests))
    return data


class BaseUsage(object):
    show_terminated = False

    def __init__(self, request, project_id=None):
        self.project_id = project_id or request.user.tenant_id
        self.request = request
        self.summary = {}
        self.usage_list = []
        self.limits = {}
        self.quotas = {}

    @property
    def today(self):
        return timezone.now()

    @staticmethod
    def get_start(year, month, day):
        start = datetime.datetime(year, month, day, 0, 0, 0)
        return timezone.make_aware(start, timezone.utc)

    @staticmethod
    def get_end(year, month, day):
        end = datetime.datetime(year, month, day, 23, 59, 59)
        return timezone.make_aware(end, timezone.utc)

    def get_date_range(self):
        if not hasattr(self, "start") or not hasattr(self, "end"):
            args_start = (self.today.year, self.today.month, 1)
            args_end = (self.today.year, self.today.month, self.today.day)
            form = self.get_form()
            if form.is_valid():
                start = form.cleaned_data['start']
                end = form.cleaned_data['end']
                args_start = (start.year,
                              start.month,
                              start.day)
                args_end = (end.year,
                            end.month,
                            end.day)
            elif form.is_bound:
                messages.error(self.request,
                               _("Invalid date format: "
                                 "Using today as default."))
        self.start = self.get_start(*args_start)
        self.end = self.get_end(*args_end)
        return self.start, self.end

    def init_form(self):
        today = datetime.date.today()
        self.start = datetime.date(day=1, month=today.month, year=today.year)
        self.end = today

        return self.start, self.end

    def get_form(self):
        if not hasattr(self, 'form'):
            req = self.request
            start = req.GET.get('start', req.session.get('usage_start'))
            end = req.GET.get('end', req.session.get('usage_end'))
            if start and end:
                # bound form
                self.form = forms.DateForm({'start': start, 'end': end})
            else:
                # non-bound form
                init = self.init_form()
                start = init[0].isoformat()
                end = init[1].isoformat()
                self.form = forms.DateForm(initial={'start': start,
                                                    'end': end})
            req.session['usage_start'] = start
            req.session['usage_end'] = end
        return self.form

    def get_domain_id(self, domain):
        if not hasattr(self, 'domain_form'):
            req = self.request
            domain_id = req.GET.get('domain_id', req.session.get('domain_id'))
            if domain_id:
                self.domain_form = DomainSelectForm(initial={'domain':domain, 'domain_id':domain_id})
            else:
                self.domain_form = DomainSelectForm(initial={'domain':domain})
            req.session['domain_id'] = domain_id
        return self.domain_form

    def get_usage_list(self, start, end):
        return []

    def summarize(self, start, end):
        if start <= end and start <= self.today:
            start = timezone.make_naive(start, timezone.utc)
            end = timezone.make_naive(end, timezone.utc)
            try:
                self.usage_list = self.get_usage_list(start, end)
            except Exception:
                exceptions.handle(self.request,
                                  _('Unable to retrieve usage information.'))
        elif end < start:
            messages.error(self.request,
                           _("Invalid time period. The end date should be "
                             "more recent than the start date."))
        elif start > self.today:
            messages.error(self.request,
                           _("Invalid time period. You are requesting "
                             "data from the future which may not exist."))
    def csv_link(self):
        form = self.get_form()
        data = {}
        if hasattr(form, "cleaned_data"):
            data = form.cleaned_data
        if not ('start' in data and 'end' in data):
            data = {"start": self.today.date(), "end": self.today.date()}
        return "?start=%s&end=%s&format=csv" % (data['start'],
                                                data['end'])


class MyUsageView(tables.DataTableView):
    usage_class = None
    show_terminated = True
    csv_template_name = None
    page_title = _("Overview")

    def __init__(self, *args, **kwargs):
        super(MyUsageView, self).__init__(*args, **kwargs)

    def get_template_names(self):
        if self.request.GET.get('format', 'html') == 'csv':
            return (self.csv_template_name or
                    ".".join((self.template_name.rsplit('.', 1)[0], 'csv')))
        return self.template_name

    def get_content_type(self):
        if self.request.GET.get('format', 'html') == 'csv':
            return "text/csv"
        return "text/html"

    def get_data(self):
        try:
            tenant_id = self.kwargs.get('tenant_id')
            self.usage_class.tenant_id = self.kwargs.get('tenant_id')
            self.usage = self.usage_class(self.request, tenant_id)
            self.usage.summarize(*self.usage.get_date_range())
            return self.usage.usage_list
        except Exception:
            exceptions.handle(self.request,
                              _('Unable to retrieve domain information.'))
            return []

    def get_context_data(self, **kwargs):
        context = super(MyUsageView, self).get_context_data(**kwargs)
        context['table'].kwargs['usage'] = self.usage
        context['form'] = self.usage.form
        context['usage'] = self.usage
        return context

    def render_to_response(self, context, **response_kwargs):
        if self.request.GET.get('format', 'html') == 'csv':
            render_class = self.csv_response_class
            response_kwargs.setdefault("filename", "usage.csv")
        else:
            render_class = self.response_class
        context = self.render_context_with_title(context)
        resp = render_class(request=self.request,
                            template=self.get_template_names(),
                            context=context,
                            content_type=self.get_content_type(),
                            **response_kwargs)
        return resp

class DomainSelectForm(forms.Form):
    domain_id = forms.ChoiceField(label=_('Domain Select'), required=False)

    def __init__(self, *args, **kwargs):
        super(DomainSelectForm, self).__init__(*args, **kwargs)
        self.fields['domain_id'].choices = kwargs.get('initial').get('domain')
        if kwargs.get('initial').get('domain_id'):
            self.fields['domain_id'].initial = kwargs.get('initial').get('domain_id')