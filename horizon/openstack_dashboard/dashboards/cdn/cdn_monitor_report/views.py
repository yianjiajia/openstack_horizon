from django.utils.translation import ugettext_lazy as _
from horizon import tabs
from openstack_dashboard.dashboards.cdn.cdn_monitor_report \
    import tabs as project_tabs
from horizon import exceptions
from openstack_dashboard.dashboards.cdn.cdn_monitor_report import constants
from openstack_dashboard.dashboards.cdn import middware
from django.http import HttpResponse
import datetime


class IndexView(tabs.TabbedTableView):
    tab_group_class = project_tabs.MonitorReportTabs
    template_name = constants.INFO_TEMPLATE_NAME
    page_title = _("Monitor Report")

    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)
        return context


def ajax_view(request, tenant_id, domain_id):
    try:
        data = []
        midd = []
        data_type = request.GET.get('type')
        domain_id = request.GET.get('domain_id')
        start = request.GET.get('start')
        end = request.GET.get('end')
        callback = request.GET.get('callback')
        if not domain_id:
            return HttpResponse(callback+'('+str([])+');', content_type='application/json')
        report_class = middware.ReportManage()
        ReportForm = middware.reportApi.ReportForm()
        ReportForm.dateFrom = start+' '+'00:00:00'
        date_object = datetime.datetime.strptime(end, "%Y-%m-%d")
        end = date_object + datetime.timedelta(days=1)
        ReportForm.dateTo = end.strftime("%Y-%m-%d %H:%M:%S")
        ReportForm.reportType = middware.reportApi.REPORT_TYPE_5_MINUTES
        if data_type == 'flow':
            ret = report_class.getFlowReport(ReportForm, domain_id)
            for o in ret:
                midd += o.getFlowPoints()
            if midd:
                for i in midd:
                    data.append([i.point.strftime("%Y-%m-%d %H:%M:%S"),
                                float('%0.2f' % (float(i.flow)))])
        if data_type == 'io':
            ret = report_class.getFlowReport(ReportForm, domain_id)
            for o in ret:
                midd += o.getFlowPoints()
            if midd:
                for i in midd:
                    data.append([i.point.strftime("%Y-%m-%d %H:%M:%S"),
                                float('%0.2f' % (float(i.flow)*8/float(60*5)))])
        if data_type == 'requests':
            ret = report_class.getHitReport(ReportForm, domain_id)
            for o in ret:
                midd += o.getHitPoints()
            if midd:
                for i in midd:
                    data.append([i.point.strftime("%Y-%m-%d %H:%M:%S"), int(i.hit)])
        return HttpResponse(callback+'('+str(data)+');', content_type='application/json')
    except Exception:
        exceptions.handle(request)

