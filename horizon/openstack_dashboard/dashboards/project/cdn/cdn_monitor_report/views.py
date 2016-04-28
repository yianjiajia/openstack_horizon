from django.utils.translation import ugettext_lazy as _
from horizon import tabs
from openstack_dashboard.dashboards.project.cdn.cdn_monitor_report \
    import tabs as project_tabs
from horizon import exceptions
from openstack_dashboard.dashboards.project.cdn.cdn_monitor_report import constants
from openstack_dashboard.dashboards.project.cdn import middware
from django.http import HttpResponse
from openstack_dashboard.dashboards.project.cdn.cdn_domain_manager.models import Domain


class IndexView(tabs.TabbedTableView):
    tab_group_class = project_tabs.MonitorReportTabs
    template_name = constants.INFO_TEMPLATE_NAME
    page_title = _("Monitor Report")

    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)
        return context


def ajax_view(request):
    try:
        data = []
        domain_data = []
        tenant_id = request.user.tenant_id
        data_type = request.GET.get('type')
        domain = request.GET.get('domain')
        start = request.GET.get('start')
        end = request.GET.get('end')
        callback = request.GET.get('callback')
        domain_id_list = [i.domain_id for i in
                          Domain.objects.filter(tenant_id=tenant_id)
                          if i.domain_id is not None and i.status != 'deleted']
        report_class = middware.ReportManage()
        ReportForm = middware.reportApi.ReportForm()
        ReportForm.dateFrom = start+' '+'00:00:00'
        ReportForm.dateTo = end+' '+'23:59:59'
        ReportForm.reportType = middware.reportApi.REPORT_TYPE_5_MINUTES
        d = dict()
        if data_type == 'flow':
            if domain == 'all':
                for i in domain_id_list:
                    ret = report_class.getFlowReport(ReportForm, i)
                    flowPoints = ret.getFlowPoints()
                    if flowPoints is not None:
                        for j in flowPoints:
                            domain_data.append([j.point.strftime("%Y-%m-%d %H:%M:%S"),
                                                float('%0.2f' % (float(j.flow)))])
                for k, v in domain_data:
                    d[k] = d.setdefault(k, 0.0) + float(v)
                data = sorted(map(list, d.items()))
            else:
                domain_get = Domain.objects.filter(domain_name=domain).exclude(status='deleted')
                ret = report_class.getFlowReport(ReportForm, domain_get[0].domain_id)
                flowPoints = ret.getFlowPoints()
                if flowPoints is not None:
                    for i in flowPoints:
                        data.append([i.point.strftime("%Y-%m-%d %H:%M:%S"),
                                    float('%0.2f' % (float(i.flow)))])
        if data_type == 'io':
            if domain == 'all':
                for i in domain_id_list:
                    ret = report_class.getFlowReport(ReportForm, i)
                    flowPoints = ret.getFlowPoints()
                    if flowPoints is not None:
                        for j in flowPoints:
                            domain_data.append([j.point.strftime("%Y-%m-%d %H:%M:%S"),
                                                float('%0.2f' % (float(j.flow)*8/float(60*5)))])
                for k, v in domain_data:
                    d[k] = d.setdefault(k, 0.0) + float(v)
                data = sorted(map(list, d.items()))
            else:
                domain_get = Domain.objects.filter(domain_name=domain).exclude(status='deleted')
                ret = report_class.getFlowReport(ReportForm, domain_get[0].domain_id)
                flowPoints = ret.getFlowPoints()
                if flowPoints is not None:
                    for i in flowPoints:
                        data.append([i.point.strftime("%Y-%m-%d %H:%M:%S"),
                                    float('%0.2f' % (float(i.flow)*8/float(60*5)))])
        if data_type == 'requests':
            if domain == 'all':
                for i in domain_id_list:
                    ret = report_class.getHitReport(ReportForm, i)
                    hitPoints = ret.getHitPoints()
                    if hitPoints is not None:
                        for j in ret.getHitPoints():
                            domain_data.append([j.point.strftime("%Y-%m-%d %H:%M:%S"), int(j.hit)])
                for k, v in domain_data:
                    d[k] = d.setdefault(k, 0) + int(v)
                data = sorted(map(list, d.items()))
            else:
                domain_get = Domain.objects.get(domain_name=domain)
                ret = report_class.getHitReport(ReportForm, domain_get.domain_id)
                hitPoints = ret.getHitPoints()
                if hitPoints is not None:
                    for i in hitPoints:
                        data.append([i.point.strftime("%Y-%m-%d %H:%M:%S"), int(i.hit)])
        return HttpResponse(callback+'('+str(data)+');', content_type='application/json')
    except Exception:
        exceptions.handle(request)

