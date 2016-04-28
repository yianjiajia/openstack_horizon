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
from openstack_dashboard import usage
from openstack_dashboard.dashboards.project.cdn.cdn_domain_manager.models import Domain
import memcache
import re
import datetime
from django.utils import timezone
from horizon import forms
from horizon import messages
from django.utils.translation import ugettext_lazy as _
from horizon import exceptions
from horizon import tables
from openstack_dashboard import api
from openstack_dashboard.usage import base
from django.conf import settings


sys.path.append("/etc/openstack-dashboard")
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
            memcached_servers=settings.CACHES.get("default").get("LOCATION")
            mc = memcache.Client(memcached_servers)
            domain_uuid = mc.get(domain_url)
            if domain_uuid is not None:
                url = self._url_check(domain_url)+'/'+domain_uuid+'.txt'
                html = urllib2.urlopen(url)
                uuid = html.read()
                if html.code == 200 and str(uuid) == str(domain_uuid):
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
    def __init__(self, account=None, total_flow=None, total_requests=None,
                 total_io=None, time_section=None):
        """

        :rtype : object
        """
        self.Customer_Account = account
        self.Total_Flow = total_flow
        self.Total_Requests = total_requests
        self.Total_Io = total_io
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
    def __init__(self, date=None, top_io=None, total_flow=None):
        """

        :rtype : object
        """
        self.date = date
        self.top_io = top_io
        self.total_flow = total_flow


class PureData(object):
    '''TenantStatistics object'''
    def __init__(self, cache_type=None, cache_time=None, status=None):
        """

        :rtype : object
        """
        self.cache_type = cache_type
        self.cache_time = cache_time
        self.status = status


def get_flow_report(dateFrom, dateTo):
    '''流量统计算法'''
    Flow = 0
    Kwag1 = {}
    report = ReportManage()
    ReportForm = reportApi.ReportForm(dateFrom=dateFrom, dateTo=dateTo, reportType='daily')
    tenant_list = [i.tenant_id for i in Domain.objects.all()]
    tenant_set = set(tenant_list)
    for i in tenant_set:
        domain_id_list = [j.domain_id for j in Domain.objects.filter(tenant_id=i) if j.domain_id is not None]
        for p in domain_id_list:
            ret = report.getFlowReport(ReportForm, p)
            flowPoints = ret.flowSummary
            if flowPoints is not None:
                Flow += float(flowPoints)
        Kwag1[i] = Flow
    return Kwag1


def get_hit_report(dateFrom, dateTo):
    '''请求数统计算法'''
    Hit = 0
    domain_hit = 0
    Kwag2 = {}
    report = ReportManage()
    ReportForm = reportApi.ReportForm(dateFrom=dateFrom, dateTo=dateTo, reportType='daily')
    tenant_list = [i.tenant_id for i in Domain.objects.all()]
    tenant_set = set(tenant_list)
    for i in tenant_set:
        domain_id_list = [j.domain_id for j in Domain.objects.filter(tenant_id=i) if j.domain_id is not None]
        for p in domain_id_list:
            ret = report.getHitReport(ReportForm, p)
            hit_list = ret.getHitPoints()
            if hit_list is not None:
                for k in hit_list:
                    domain_hit += int(k.hit)
                Hit += domain_hit
        Kwag2[i] = Hit
    return Kwag2


def get_all_data(dateFrom, dateTo):
    try:
        data = []
        hit_ret = get_hit_report(str(dateFrom), str(dateTo))
        flow_ret = get_flow_report(str(dateFrom), str(dateTo))
        for k in hit_ret:
            if (dateTo-dateFrom).days == 0:
                io = flow_ret[k]*8/24*60*60
            else:
                io = flow_ret[k]*8/(24*60*60*(dateTo-dateFrom).days)

            data.append(DataStatistics(account=k, total_flow=flow_ret[k],
                                       total_requests=hit_ret[k], total_io=io, time_section=(dateTo-dateFrom).days))
        return data
    except Exception:
        return []


def get_tenant_flow(dateFrom, dateTo, tenant_id=None):
    FLOW_DATA = 0.0
    Kwag1 = {}
    report = ReportManage()
    ReportForm = reportApi.ReportForm(dateFrom=dateFrom, dateTo=dateTo, reportType='daily')
    domain_id_list = [j.domain_id for j in Domain.objects.filter(tenant_id=tenant_id) if j.domain_id is not None]
    for i in domain_id_list:
        ret = report.getFlowReport(ReportForm, i)
        flowPoints = ret.flowSummary
        if flowPoints is not None:
            FLOW_DATA += float(flowPoints)
        Kwag1[i] = FLOW_DATA
    return Kwag1


def get_tenant_hit(dateFrom, dateTo, tenant_id=None):
    Hit = 0
    domain_hit = 0
    Kwag2 = {}
    report = ReportManage()
    ReportForm = reportApi.ReportForm(dateFrom=dateFrom, dateTo=dateTo, reportType='daily')
    domain_id_list = [j.domain_id for j in Domain.objects.filter(tenant_id=tenant_id) if j.domain_id is not None]
    for i in domain_id_list:
        ret = report.getHitReport(ReportForm, i)
        hit_list = ret.getHitPoints()
        if hit_list is not None:
            for k in hit_list:
                domain_hit += int(k.hit)
        Hit += domain_hit
        Kwag2[i] = Hit
    return Kwag2


def get_tenant_data(dateFrom, dateTo, tenant_id):
    try:
        data = []
        flow_ret = get_tenant_flow(dateFrom.strftime("%Y-%m-%d %H:%M:%S"), dateTo.strftime("%Y-%m-%d %H:%M:%S"), tenant_id)
        hit_ret = get_tenant_hit(dateFrom.strftime("%Y-%m-%d %H:%M:%S"), dateTo.strftime("%Y-%m-%d %H:%M:%S"), tenant_id)
        domain_name_list = [j for j in Domain.objects.filter(tenant_id=tenant_id) if j.domain_id is not None]
        for k in flow_ret:
            for p in domain_name_list:
                if p.domain_id == k:
                    if (dateTo-dateFrom).days == 0:
                        io = flow_ret[k]*8/24*60*60
                    else:
                        io = flow_ret[k]*8/(24*60*60*(dateTo-dateFrom).days)
                    data.append(TenantStatistics(domain=p.domain_name, month=str(dateFrom.strftime('%Y-%m')),
                                                 flow=flow_ret[k], requests=hit_ret[k], io=io))
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


def get_mon_data(dateFrom, dateTo, tenant_id):
    data = []
    domain_data = []
    domain_id_list = [i.domain_id for i in Domain.objects.filter(tenant_id=tenant_id) if i.domain_id is not None]
    report_class = ReportManage()
    ReportForm = reportApi.ReportForm(dateFrom, dateTo, reportType='fiveminutes')
    d = {}
    IO = {}
    for i in domain_id_list:
        ret = report_class.getFlowReport(ReportForm, i)
        flowPoints = ret.getFlowPoints()
        if flowPoints is not None:
            for j in flowPoints:
                domain_data.append([j.point.strftime("%Y-%m-%d"), float('%0.2f' % (float(j.flow)))])
            for k, v in domain_data:
                d[k] = d.setdefault(k, 0.0) + float(v)
                IO[k] = IO.setdefault(k, []) + [v]
    for k in sorted(d):
        io = max(IO[k])*8/(5*60)
        data.append(MonData(date=k, top_io=io, total_flow=d[k]))
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

    def get_instances(self):
        instance_list = []
        [instance_list.extend(u.server_usages) for u in self.usage_list]
        return instance_list

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