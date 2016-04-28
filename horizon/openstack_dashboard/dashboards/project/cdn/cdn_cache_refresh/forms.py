__author__ = 'yanjiajia'
from horizon import forms
from django.utils.translation import ugettext_lazy as _


class UrlFreshForm(forms.Form):
    url_fresh = forms.URLField(label=_("Url Fresh"), max_length=64,
                               widget=forms.Textarea(attrs={'cols': 70, 'rows': 10}),
                               required=True)


class DirFreshForm(forms.Form):
    Dir_fresh = forms.URLField(label=_("Directory Fresh"), max_length=64,
                               widget=forms.Textarea(attrs={'cols': 70, 'rows': 10}),
                               required=True)

