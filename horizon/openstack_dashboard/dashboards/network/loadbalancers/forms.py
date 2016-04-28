# Copyright 2013, Mirantis Inc
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

import logging

from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import forms
from horizon import messages

from openstack_dashboard import api


LOG = logging.getLogger(__name__)


class UpdatePool(forms.SelfHandlingForm):
    name = forms.CharField(max_length=80, label=_("Name"))
    pool_id = forms.CharField(label=_("ID"),
                              widget=forms.TextInput(
                                  attrs={'readonly': 'readonly'}))
    description = forms.CharField(required=False,
                                  max_length=80, label=_("Description"))
    lb_method = forms.ChoiceField(label=_("Load Balancing Method"))
    admin_state_up = forms.ChoiceField(choices=[(True, _('UP')),
                                                (False, _('DOWN'))],
                                       label=_("Admin State"))

    failure_url = 'horizon:network:loadbalancers:index'

    def __init__(self, request, *args, **kwargs):
        super(UpdatePool, self).__init__(request, *args, **kwargs)

        lb_method_choices = [('ROUND_ROBIN', 'ROUND_ROBIN'),
                             ('LEAST_CONNECTIONS', 'LEAST_CONNECTIONS'),
                             ('SOURCE_IP', 'SOURCE_IP')]
        self.fields['lb_method'].choices = lb_method_choices

    def handle(self, request, context):
        context['admin_state_up'] = (context['admin_state_up'] == 'True')
        try:
            data = {'pool': {'name': context['name'],
                             'description': context['description'],
                             'lb_method': context['lb_method'],
                             'admin_state_up': context['admin_state_up'],
                             }}
            pool = api.lbaas.pool_update(request, context['pool_id'], **data)
            msg = _('Pool %s was successfully updated.') % context['name']
            LOG.debug(msg)
            messages.success(request, msg)

            # operation log
            config = _('Pool Name: %s') %context['name']

            api.logger.Logger(request).create(resource_type='loadblance', action_name='Update Loadblance',
                                                       resource_name='Loadblance', config=config,
                                                       status='Success')
            return pool
        except Exception:
            msg = _('Failed to update pool %s') % context['name']
            LOG.info(msg)
            redirect = reverse(self.failure_url)
            exceptions.handle(request, msg, redirect=redirect)

            # operation log
            api.logger.Logger(request).create(resource_type='loadblance', action_name='Update Loadblance',
                                                       resource_name='Loadblance', config=msg,
                                                       status='Error')


class UpdateVip(forms.SelfHandlingForm):
    name = forms.CharField(max_length=80, label=_("Name"))
    vip_id = forms.CharField(label=_("ID"),
                             widget=forms.TextInput(
                                 attrs={'readonly': 'readonly'}))
    description = forms.CharField(required=False,
                                  max_length=80, label=_("Description"))
    pool_id = forms.ChoiceField(label=_("Pool"))
    session_persistence = forms.ChoiceField(
        required=False, initial={}, label=_("Session Persistence"))

    cookie_name = forms.CharField(
        initial="", required=False,
        max_length=80, label=_("Cookie Name"),
        help_text=_("Required for APP_COOKIE persistence;"
                    " Ignored otherwise."))

    connection_limit = forms.IntegerField(
        min_value=-1, label=_("Connection Limit"),
        help_text=_("Maximum number of connections allowed "
                    "for the VIP or '-1' if the limit is not set"))
    admin_state_up = forms.ChoiceField(choices=[(True, _('UP')),
                                                (False, _('DOWN'))],
                                       label=_("Admin State"))

    failure_url = 'horizon:network:loadbalancers:index'

    def __init__(self, request, *args, **kwargs):
        super(UpdateVip, self).__init__(request, *args, **kwargs)

        pool_id_choices = []
        try:
            tenant_id = request.user.tenant_id
            pools = api.lbaas.pool_list(request, tenant_id=tenant_id)
        except Exception:
            pools = []
            exceptions.handle(request,
                              _('Unable to retrieve pools list.'))
        pools = sorted(pools,
                       key=lambda pool: pool.name)
        for p in pools:
            if (p.vip_id is None) or (p.id == kwargs['initial']['pool_id']):
                pool_id_choices.append((p.id, p.name))
        self.fields['pool_id'].choices = pool_id_choices

        session_persistence_choices = []
        for mode in ('SOURCE_IP', 'HTTP_COOKIE', 'APP_COOKIE'):
            session_persistence_choices.append((mode, mode))
        session_persistence_choices.append(('', _('No session persistence')))
        self.fields[
            'session_persistence'].choices = session_persistence_choices

    def clean(self):
        cleaned_data = super(UpdateVip, self).clean()

        persistence = cleaned_data.get('session_persistence')
        if (persistence == 'APP_COOKIE' and
                not cleaned_data.get('cookie_name')):
            msg = _('Cookie name is required for APP_COOKIE persistence.')
            self._errors['cookie_name'] = self.error_class([msg])
        return cleaned_data

    def handle(self, request, context):
        context['admin_state_up'] = (context['admin_state_up'] == 'True')
        if context['session_persistence']:
            stype = context['session_persistence']
            if stype == 'APP_COOKIE':
                cookie = context['cookie_name']
                context['session_persistence'] = {'type': stype,
                                                  'cookie_name': cookie}
            else:
                context['session_persistence'] = {'type': stype}
        else:
            context['session_persistence'] = {}

        try:
            data = {'vip': {'name': context['name'],
                            'description': context['description'],
                            'pool_id': context['pool_id'],
                            'session_persistence':
                                context['session_persistence'],
                            'connection_limit': context['connection_limit'],
                            'admin_state_up': context['admin_state_up'],
                            }}
            vip = api.lbaas.vip_update(request, context['vip_id'], **data)
            msg = _('VIP %s was successfully updated.') % context['name']
            LOG.debug(msg)
            messages.success(request, msg)

            # operation log
            config = _('Vip Name: %s') %context['name']

            api.logger.Logger(request).create(resource_type='loadblance', action_name='Update Loadblance Vip',
                                                       resource_name='Loadblance', config=config,
                                                       status='Success')

            return vip
        except Exception:
            msg = _('Failed to update VIP %s') % context['name']
            LOG.info(msg)
            redirect = reverse(self.failure_url)
            exceptions.handle(request, msg, redirect=redirect)

            # operation log
            api.logger.Logger(request).create(resource_type='loadblance', action_name='Update Loadblance Vip',
                                                       resource_name='Loadblance', config=msg,
                                                       status='Error')


class UpdateMember(forms.SelfHandlingForm):
    member_id = forms.CharField(label=_("ID"),
                                widget=forms.TextInput(
                                    attrs={'readonly': 'readonly'}))
    pool_id = forms.ChoiceField(label=_("Pool"))
    weight = forms.IntegerField(max_value=256, min_value=0, label=_("Weight"),
                                help_text=_("Relative part of requests this "
                                "pool member serves compared to others"))
    admin_state_up = forms.ChoiceField(choices=[(True, _('UP')),
                                                (False, _('DOWN'))],
                                       label=_("Admin State"))

    failure_url = 'horizon:network:loadbalancers:index'

    def __init__(self, request, *args, **kwargs):
        super(UpdateMember, self).__init__(request, *args, **kwargs)

        pool_id_choices = []
        try:
            tenant_id = request.user.tenant_id
            pools = api.lbaas.pool_list(request, tenant_id=tenant_id)
        except Exception:
            pools = []
            exceptions.handle(request,
                              _('Unable to retrieve pools list.'))
        pools = sorted(pools,
                       key=lambda pool: pool.name)
        for p in pools:
            pool_id_choices.append((p.id, p.name))
        self.fields['pool_id'].choices = pool_id_choices

    def handle(self, request, context):
        context['admin_state_up'] = (context['admin_state_up'] == 'True')
        try:
            data = {'member': {'pool_id': context['pool_id'],
                               'weight': context['weight'],
                               'admin_state_up': context['admin_state_up']}}
            member = api.lbaas.member_update(request,
                                             context['member_id'], **data)
            msg = _('Member %s was successfully updated.')\
                % context['member_id']
            LOG.debug(msg)
            messages.success(request, msg)
            return member
        except Exception:
            msg = _('Failed to update member %s') % context['member_id']
            LOG.info(msg)
            redirect = reverse(self.failure_url)
            exceptions.handle(request, msg, redirect=redirect)


class UpdateMonitor(forms.SelfHandlingForm):
    monitor_id = forms.CharField(label=_("ID"),
                                 widget=forms.TextInput(
                                     attrs={'readonly': 'readonly'}))
    delay = forms.IntegerField(
        min_value=1,
        label=_("Delay"),
        help_text=_("The minimum time in seconds between regular checks "
                    "of a member"))
    timeout = forms.IntegerField(
        min_value=1,
        label=_("Timeout"),
        help_text=_("The maximum time in seconds for a monitor to wait "
                    "for a reply"))
    max_retries = forms.IntegerField(
        max_value=10, min_value=1,
        label=_("Max Retries (1~10)"),
        help_text=_("Number of permissible failures before changing "
                    "the status of member to inactive"))
    admin_state_up = forms.ChoiceField(choices=[(True, _('UP')),
                                                (False, _('DOWN'))],
                                       label=_("Admin State"))

    failure_url = 'horizon:network:loadbalancers:index'

    def __init__(self, request, *args, **kwargs):
        super(UpdateMonitor, self).__init__(request, *args, **kwargs)

    def handle(self, request, context):
        context['admin_state_up'] = (context['admin_state_up'] == 'True')
        try:
            data = {'health_monitor': {
                    'delay': context['delay'],
                    'timeout': context['timeout'],
                    'max_retries': context['max_retries'],
                    'admin_state_up': context['admin_state_up']}}
            monitor = api.lbaas.pool_health_monitor_update(
                request, context['monitor_id'], **data)
            msg = _('Health monitor %s was successfully updated.')\
                % context['monitor_id']
            LOG.debug(msg)
            messages.success(request, msg)
            return monitor
        except Exception:
            msg = _('Failed to update health monitor %s')\
                % context['monitor_id']
            LOG.info(msg)
            redirect = reverse(self.failure_url)
            exceptions.handle(request, msg, redirect=redirect)


class UpdateLoadBalancer(forms.SelfHandlingForm):
#     admin_state_up = forms.ChoiceField(choices=[(True, _('UP')),
#                                                 (False, _('DOWN'))],
#                                        label=_("Admin State"))
    pool_id = forms.CharField(label=_("ID"),
                              widget=forms.HiddenInput)
    name = forms.CharField(max_length=80, label=_("Name"))
#     protocol = forms.ChoiceField(label=_("Protocol"))
    lb_method = forms.ChoiceField(label=_("Load Balancing Method"))
    protocol_port = forms.IntegerField(label=_("Port"))
    vip_id = forms.CharField(label=_("ID"),
                             widget=forms.HiddenInput)
    session_persistence = forms.ChoiceField(
        required=False, initial={}, label=_("Session Persistence"))
    cookie_name = forms.CharField(
        initial="", required=False,
        max_length=80, label=_("Cookie Name"),
        help_text=_("Required for APP_COOKIE persistence;"
                    " Ignored otherwise."))
    connection_limit = forms.ChoiceField(
        required=False,label=_("Connection Limit"),
        choices=[('5000', _('5,000')),
                 ('20000', _('20,000')),
                 ('40000', _('40,000')),
                 ('100000', _('100,000'))],
        help_text=_("Maximum number of connections allowed "))
    set_health_check = forms.ChoiceField(
            label=_("Set Health"),
            help_text=_("set Health check, if checked, need set type,delay,timeout,max_retries"),
            required = False,
            initial = True,
            choices=[('-1', _('Please select if set health check')),
                     ('True', _('true')),
                     ('False', _('false'))]
            )
    # monitor
    type = forms.ChoiceField(
        label=_("Type"),
        choices=[('ping', _('PING')),
                 ('tcp', _('TCP')),
                 ('http', _('HTTP')),
                 ('https', _('HTTPS'))],
        required = False,
        widget=forms.Select(attrs={
            'class': 'switchable',
            'data-slug': 'type'
        }))
    monitor_id = forms.CharField(label=_("ID"),
                                 required = False,
                                 widget=forms.HiddenInput)
    delay = forms.IntegerField(
        min_value=1,
        label=_("Delay"),
        required = False,
        help_text=_("The minimum time in seconds between regular checks "
                    "of a member"))
    timeout = forms.IntegerField(
        min_value=1,
        label=_("Timeout"),
        required = False,
        help_text=_("The maximum time in seconds for a monitor to wait "
                    "for a reply"))
    max_retries = forms.IntegerField(
        max_value=10, min_value=1,
        label=_("Max Retries (1~10)"),
        required = False,
        help_text=_("Number of permissible failures before changing "
                    "the status of member to inactive"))
    url_path = forms.CharField(
        initial="/",
        required=False,
        max_length=80,
        label=_("URL"),
        widget=forms.TextInput(attrs={
            'class': 'switched',
            'data-switch-on': 'type',
            'data-type-http': _('URL'),
            'data-type-https': _('URL')
        }))

    failure_url = 'horizon:network:loadbalancers:index'

    def __init__(self, request, *args, **kwargs):
        super(UpdateLoadBalancer, self).__init__(request, *args, **kwargs)
        AVAILABLE_PROTOCOLS = ('HTTP', 'HTTPS', 'TCP')
        protocol_choices = [('', _("Select a Protocol"))]
        [protocol_choices.append((p, p)) for p in AVAILABLE_PROTOCOLS]
#         self.fields['protocol'].choices = protocol_choices
        lb_method_choices = [('ROUND_ROBIN', 'ROUND_ROBIN'),
                             ('LEAST_CONNECTIONS', 'LEAST_CONNECTIONS'),
                             ('SOURCE_IP', 'SOURCE_IP')]
        self.fields['lb_method'].choices = lb_method_choices

        session_persistence_choices = []
        for mode in ('SOURCE_IP', 'HTTP_COOKIE', 'APP_COOKIE'):
            session_persistence_choices.append((mode, mode))
        session_persistence_choices.append(('', _('No session persistence')))
        self.fields[
            'session_persistence'].choices = session_persistence_choices

    def clean(self):
        cleaned_data = super(UpdateLoadBalancer, self).clean()

        type_opt = cleaned_data.get('type')
        delay = cleaned_data.get('delay')
        timeout = cleaned_data.get('timeout')

        if not delay >= timeout:
            msg = _('Delay must be greater than or equal to Timeout')
            self._errors['delay'] = self.error_class([msg])

        if type_opt in ['http', 'https']:
            # set default for http_method  expected_codes
            cleaned_data['http_method'] = 'Get'
            cleaned_data['expected_codes'] = '200'
            http_method_opt = cleaned_data.get('http_method')
            url_path = cleaned_data.get('url_path')
            expected_codes = cleaned_data.get('expected_codes')

            if not http_method_opt:
                msg = _('Please choose a HTTP method')
                self._errors['http_method'] = self.error_class([msg])
            if not url_path:
                msg = _('Please specify an URL')
                self._errors['url_path'] = self.error_class([msg])
            if not expected_codes:
                msg = _('Please enter a single value (e.g. 200), '
                        'a list of values (e.g. 200, 202), '
                        'or range of values (e.g. 200-204)')
                self._errors['expected_codes'] = self.error_class([msg])

        persistence = cleaned_data.get('session_persistence')
        if (persistence == 'APP_COOKIE' and
                not cleaned_data.get('cookie_name')):
            msg = _('Cookie name is required for APP_COOKIE persistence.')
            self._errors['cookie_name'] = self.error_class([msg])
        if type_opt:
            cleaned_data['type'] = type_opt.upper()
        return cleaned_data

    def handle(self, request, context):
        if context['session_persistence']:
            stype = context['session_persistence']
            if stype == 'APP_COOKIE':
                cookie = context['cookie_name']
                context['session_persistence'] = {'type': stype,
                                                  'cookie_name': cookie}
            else:
                context['session_persistence'] = {'type': stype}
        else:
            context['session_persistence'] = {}
        try:
            data = {'pool': {'name': context['name'],
                             'lb_method': context['lb_method'],
#                             'protocol': context['protocol'],
                             }}
            pool = api.lbaas.pool_update(request, context['pool_id'], **data)
            data = {'vip': {'name': context['name'],
                            'session_persistence':context['session_persistence'],
                            'connection_limit': context['connection_limit'],
#                             'protocol' : context['protocol'],
                            'protocol_port' : context['protocol_port'],
                            }}
            vip = api.lbaas.vip_update(request, context['vip_id'], **data)

            if context['set_health_check'] == 'True':
                # set default for http_method  expected_codes
                context['http_method'] = 'Get'
                context['expected_codes'] = '200'
                data = {
                        'type': context['type'],
                        'delay': context['delay'],
                        'timeout': context['timeout'],
                        'max_retries': context['max_retries'],
                        'url_path': context['url_path'],
                        'http_method': context['http_method'],
                        'expected_codes': context['expected_codes']}
                if len(pool.health_monitors) == 0:
                    data['admin_state_up'] = True
                    monitor = api.lbaas.pool_health_monitor_create(request, **data)
                    context['monitor_id'] = monitor.id
                    context['pool_id'] = pool.id
                    api.lbaas.pool_monitor_association_create(request, **context)
                else:
                    data = {'health_monitor' : data}
                    monitor = api.lbaas.pool_health_monitor_update(request, context['monitor_id'], **data)
            else:
                if len(pool.health_monitors) > 0:
                    for hm in pool.health_monitors:
                        context['pool_id'] = pool.id
                        context['monitor_id'] = hm
                        context['monitor_id'] = api.lbaas.pool_monitor_association_delete(
                request, **context)
                        api.lbaas.pool_health_monitor_delete(request, hm)

            msg = _('Loadbalancer %s was successfully updated.') % context['name']
            LOG.debug(msg)
            messages.success(request, msg)

            # operation log
            config = _('Loadblance Name: %s') % context['name']

            api.logger.Logger(request).create(resource_type='loadblance', action_name='Update Loadblance',
                                                       resource_name='Loadblance', config=config,
                                                       status='Success')
            return pool
        except Exception:
            msg = _('Failed to update Loadbalancer %s') % context['name']
            LOG.info(msg)
            redirect = reverse(self.failure_url)
            exceptions.handle(request, msg, redirect=redirect)

            # operation log

            api.logger.Logger(request).create(resource_type='loadblance', action_name='Update Loadblance',
                                                       resource_name='Loadblance', config=msg,
                                                       status='Error')
