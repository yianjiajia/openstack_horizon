__author__ = 'yanjiajia'
from horizon import tables
from django.utils.translation import ugettext_lazy as _
from django.template.defaultfilters import floatformat
from horizon.templatetags import sizeformat


class UsageTable(tables.DataTable):
    date = tables.Column('date', verbose_name=_("Date"))
    top_io = tables.Column('top_io', verbose_name=_("IO(Mb/s)"), filters=(lambda v: floatformat(v, 2),))
    total_flow = tables.Column('total_flow', verbose_name=_("Total Flow"),
                               filters=(lambda v: floatformat(v, 2), sizeformat.mb_float_format))

    def get_object_id(self, datum):
        return datum.date

    class Meta(object):
        name = "usage"
        verbose_name = _("Usage")

