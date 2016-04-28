# Copyright 2013 CentRin Data, Inc.
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


import json

from django.utils.translation import ugettext_lazy as _
from django.views.decorators.debug import sensitive_variables  # noqa

from horizon import exceptions
from horizon import forms
from horizon import workflows
from openstack_dashboard import api
from openstack_dashboard.dashboards.instances.instances \
    import utils as instance_utils
from openstack_dashboard.dashboards.instances.instances.workflows \
    import create_instance
from openstack_dashboard.usage import quotas


class SetFlavorChoiceAction(workflows.Action):
    # change by zhihao.ding 2015/7/16 for kill_flavor start
    #old_flavor_id = forms.CharField(required=False, widget=forms.HiddenInput())
    #old_flavor_name = forms.CharField(
    #    label=_("Old Flavor"),
    #    widget=forms.TextInput(attrs={'readonly': 'readonly'}),
    #    required=False,
    #)
    #flavor = forms.ChoiceField(label=_("New Flavor"),
    #                           help_text=_("Choose the flavor to launch."))

    instance_id = forms.CharField(label=_("Instance ID"),
                                  widget=forms.HiddenInput(),
                                  required=False)

    old_vcpus = forms.CharField(
        label=_("Old vCPUs"),
        widget=forms.TextInput(attrs={'readonly': 'readonly'}),
        required=False,
    )
    
    old_memory_mb = forms.CharField(
        label=_("Old Memory(MB)"),
        widget=forms.TextInput(attrs={'readonly': 'readonly'}),
        required=False,
    )
    
    vcpus = forms.ChoiceField(label=_("New vCPUs"), 
                              help_text=_("Number of vCPUs."),
                              choices= [('2', '2'),  ('4', '4'), ('8', '8'),  ('16', '16'), ('24', '24'), ('32', '32')])
                              
    memory_mb = forms.ChoiceField(label=_("New Memory Size"), 
                                  help_text=_("Size of memory."),
                                  choices=[('2048',  '2GB'),
                                           ('4096',  '4GB'), ('8192', '8GB'), ('16384',  '16GB'), ('32768', '32GB'), ('65536', '64GB')])
    # change by zhihao.ding 2015/7/16 for kill_flavor end

    class Meta(object):
        name = _("Flavor Choice")
        slug = 'flavor_choice'
        help_text_template = ("instances/instances/"
                              "_flavors_and_quotas.html")

    # change by zhihao.ding 2015/7/17 for kill_flavor start
    '''
    def populate_flavor_choices(self, request, context):
        old_flavor_id = context.get('old_flavor_id')
        flavors = context.get('flavors').values()

        # Remove current flavor from the list of flavor choices
        flavors = [flavor for flavor in flavors if flavor.id != old_flavor_id]
        if len(flavors) > 1:
            flavors = instance_utils.sort_flavor_list(request, flavors)
        if flavors:
            flavors.insert(0, ("", _("Select a New Flavor")))
        else:
            flavors.insert(0, ("", _("No flavors available")))
        return flavors
    '''
    def _check_ram_vcpus(self, cleaned_data):
        vcpus = int(cleaned_data['vcpus'])
        ram = int(cleaned_data['memory_mb'])
        
        count_error = []
        # Validate cores and ram.
        usages = quotas.tenant_quota_usages(self.request)
        available_cores = usages['cores']['available']
        if vcpus and available_cores < vcpus:
            count_error.append(_("Cores(Available: %(avail)s, "
                                 "Requested: %(req)s)")
                               % {'avail': available_cores,
                                  'req': vcpus})

        available_ram = usages['ram']['available']
        if ram and available_ram < ram:
            count_error.append(_("RAM(Available: %(avail)s, "
                                 "Requested: %(req)s)")
                               % {'avail': available_ram,
                                  'req': ram})

        if count_error:
            value_str = ", ".join(count_error)
            msg = (_('The requested instance cannot be launched. '
                     'The following requested resource(s) exceed '
                     'quota(s): %s.') % value_str)
            self._errors['flavor'] = self.error_class([msg])
    
    def clean(self):
        cleaned_data = super(SetFlavorChoiceAction, self).clean()
        #print "[DINGZHIHAO][clean] cleaned_data:", cleaned_data
        self._check_ram_vcpus(cleaned_data)
        return cleaned_data
    # change by zhihao.ding 2015/7/17 for kill_flavor end

    def get_help_text(self, extra_context=None):
        extra = {} if extra_context is None else dict(extra_context)
        try:
            extra['usages'] = api.nova.tenant_absolute_limits(self.request)
            extra['usages_json'] = json.dumps(extra['usages'])
            # delete by zhihao.ding 2015/7/17 for kill_flavor start
            #flavors = json.dumps([f._info for f in
            #                      instance_utils.flavor_list(self.request)])
            #extra['flavors'] = flavors
            # delete by zhihao.ding 2015/7/17 for kill_flavor start
            extra['resize_instance'] = True
        except Exception:
            exceptions.handle(self.request,
                              _("Unable to retrieve quota information."))
        return super(SetFlavorChoiceAction, self).get_help_text(extra)


class SetFlavorChoice(workflows.Step):
    action_class = SetFlavorChoiceAction
    depends_on = ("instance_id", "name")
    #change by zhihao.ding 2015/7/17 for kill_flavor start
    #contributes = ("old_flavor_id", "old_flavor_name", "flavors", "flavor")
    contributes = ("old_memory_mb", "old_vcpus", "memory_mb", "vcpus")
    #change by zhihao.ding 2015/7/17 for kill_flavor start


class ResizeInstance(workflows.Workflow):
    slug = "resize_instance"
    name = _("Resize Instance")
    finalize_button_name = _("Resize")
    success_message = _('Scheduled resize of instance "%s".')
    failure_message = _('Unable to resize instance "%s".')
    success_url = "horizon:instances:instances:index"
    default_steps = (SetFlavorChoice, create_instance.SetAdvanced)

    def format_status_message(self, message):
        return message % self.context.get('name', 'unknown instance')

    @sensitive_variables('context')
    def handle(self, request, context):
        instance_id = context.get('instance_id', None)
        #flavor = context.get('flavor', None)
        disk_config = context.get('disk_config', None)
        
		# add by zhihao.ding 2015/7/20 for kill_flavor start
        flavor = {}
        flavor['vcpus'] = context.get('vcpus')
        flavor['memory_mb'] = context.get('memory_mb')
        # add by zhihao.ding 2015/7/20 for kill_flavor end
       
        try:
            instance = api.nova.server_get(request, instance_id)
            api.nova.server_resize(request, instance_id, flavor, disk_config)

            # operation log
            config = _("Instance Name: %s Cpu: %s Memory: %s Disk Config: %s") %(instance.name, str(context.get('vcpus')),
                                                                              str(context.get('memory_mb')), disk_config)
            api.logger.Logger(request).create(resource_type='instance', action_name='Resize Instance',
                                                       resource_name='Instance', config=config,
                                                       status='Success')
            return True
        except Exception:
            exceptions.handle(request)

            # operation log
            api.logger.Logger(request).create(resource_type='instance', action_name='Resize Instance',
                                                       resource_name='Instance', config='',
                                                       status='Error')
            return False
