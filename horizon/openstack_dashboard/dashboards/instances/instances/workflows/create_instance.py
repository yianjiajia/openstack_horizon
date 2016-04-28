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
import json
import logging
import operator
import time
from oslo_utils import units
from django.forms import ValidationError
from django.utils.text import normalize_newlines  # noqa
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext_lazy
from django.views.decorators.debug import sensitive_variables  # noqa

from horizon import exceptions
from horizon import forms
from horizon.utils import functions
from horizon.utils import memoized
from horizon.utils import validators
from horizon import workflows
from horizon.utils import userdata
from horizon.utils import units as horizon_units
from local_settings import SHOW_MIN_CHOICES_FOR_TEST

from openstack_dashboard import api
from openstack_dashboard.api import base
from openstack_dashboard.api import cinder
from openstack_dashboard.api import nova
from openstack_dashboard.usage import quotas
from openstack_dashboard.dashboards.instances.images \
    import utils as image_utils
from openstack_dashboard.dashboards.instances.instances \
    import utils as instance_utils

LOG = logging.getLogger(__name__)


class SelectProjectUserAction(workflows.Action):
    project_id = forms.ChoiceField(label=_("Project"))
    user_id = forms.ChoiceField(label=_("User"))

    def __init__(self, request, *args, **kwargs):
        super(SelectProjectUserAction, self).__init__(request, *args, **kwargs)
        # Set our project choices
        projects = [(tenant.id, tenant.name)
                    for tenant in request.user.authorized_tenants]
        self.fields['project_id'].choices = projects

        # Set our user options
        users = [(request.user.id, request.user.username)]
        self.fields['user_id'].choices = users

    class Meta(object):
        name = _("Project & User")
        # Unusable permission so this is always hidden. However, we
        # keep this step in the workflow for validation/verification purposes.
        permissions = ("!",)


class SelectProjectUser(workflows.Step):
    action_class = SelectProjectUserAction
    contributes = ("project_id", "user_id")


class SelectImageAction(workflows.MembershipAction):
    availability_zone = forms.ChoiceField(label=_("Availability Zone"),
                                          required=False)
    # change by zhihao.ding 2015/7/16 for kill_flavor start
    #flavor = forms.ChoiceField(label=_("Flavor"),
    #                          help_text=_("Size of image to launch."))
    # vcpus = forms.ChoiceField(label=_("vCPUs"), required=False, help_text=_("Number of vCPUs."))
    # memory_mb = forms.ChoiceField(label=_("Memory Size"), required=False, help_text=_("Size of memory."))
    # change by zhihao.ding 2015/7/16 for kill_flavor end

    # count = forms.IntegerField(label=_("Instance Count"),
    #                            min_value=1,
    #                            initial=1,
    #                            help_text=_("Number of instances to launch."))

    image_type = forms.ChoiceField(label=_("Instance Boot Source"),
                                    help_text=_("Choose Your Boot Source "
                                                "Type."), required=False)

    instance_snapshot_id = forms.ChoiceField(label=_("Instance Snapshot"),
                                             required=False)

    volume_id = forms.ChoiceField(label=_("Volume"), required=False)

    volume_snapshot_id = forms.ChoiceField(label=_("Volume Snapshot"),
                                           required=False)
    custom_image = forms.ChoiceField(label=_("Custom Image"),
                                           required=False)

    # image_id = forms.ChoiceField(
    #     label=_("Image Name"),
    #     required=False,
    #     widget=forms.SelectWidget(
    #         data_attrs=('volume_size',),
    #         transform=lambda x: ("%s (%s)" % (x.name,
    #                                           filesizeformat(x.bytes)))))

    volume_size = forms.IntegerField(label=_("Device size (GB)"),
                                     initial=1,
                                     min_value=0,
                                     required=False,
                                     help_text=_("Volume size in gigabytes "
                                                 "(integer value)."))

    device_name = forms.CharField(label=_("Device Name"),
                                  required=False,
                                  initial="vda",
                                  help_text=_("Volume mount point (e.g. 'vda' "
                                              "mounts at '/dev/vda'). Leave "
                                              "this field blank to let the "
                                              "system choose a device name "
                                              "for you."))
    # delete_on_terminate = forms.BooleanField(label=_("Delete on Terminate"),
    #                                          initial=False,
    #                                          required=False,
    #                                          help_text=_("Delete volume on "
    #                                                      "instance terminate"))

    class Meta(object):
        name = _("Select Image")
        slug = 'selectimage'

    def __init__(self, request, context, *args, **kwargs):
        self._init_images_cache()
        self.request = request
        self.context = context
        super(SelectImageAction, self).__init__(
            request, context, *args, **kwargs)
        # Hide the device field if the hypervisor doesn't support it.
        default_role_name = self.get_default_role_field_name()
        self.fields[default_role_name] = forms.CharField(label='', required=False,
                                                         widget=forms.TextInput(attrs={'style': 'display: none'}))
        self.fields[default_role_name].initial = 'default'
        if not nova.can_set_mount_point():
            self.fields['device_name'].widget = forms.widgets.HiddenInput()
        self.fields['volume_size'].widget = forms.widgets.HiddenInput()
        # source_type_choices = [
        #     ('', _("Select source")),
        #     #("image_id", _("Boot from image")),
        #     #("instance_snapshot_id", _("Boot from snapshot")),
        # ]
        # if base.is_service_enabled(request, 'volume'):
        #     source_type_choices.append(("volume_id", _("Boot from volume")))
        #
        #     try:
        #         if api.nova.extension_supported("BlockDeviceMappingV2Boot",
        #                                         request):
        #             source_type_choices.append(
        #                 ("volume_image_id",
        #                  _("Boot from image (creates a new volume)")))
        #     except Exception:
        #         exceptions.handle(request, _('Unable to retrieve extensions '
        #                                      'information.'))
        #
        #     source_type_choices.append(
        #         ("volume_snapshot_id",
        #          _("Boot from volume snapshot (creates a new volume)")))
        self.fields['image_type'].choices = [('volume_image_id', 'volume_image_id')]
        role = {'id': 'image_id', 'name': 'image_id'}
        field_name = self.get_member_field_name(role['id'])
        self.fields[field_name] = forms.ChoiceField(label='', required=False,
                                                    widget=forms.SelectWidget(attrs={'style': 'display:none'}))
        image_list = api.glance.image_list_detailed(request)
        public_image_list = [(i.id, i.name) for i in image_list[0] if i.is_public]
        custom_image_list = [(i.id, i.name) for i in image_list[0] if not i.is_public]
        public_image_list.sort(key=lambda c: c[1])
        custom_image_list.sort(key=lambda c: c[1])
        public_image_list.insert(0, ('', ''))
        self.fields[field_name].choices = public_image_list
        self.fields[field_name].initial = []
        custom_image_list.insert(0, ('', ''))
        self.fields['custom_image'].choices = custom_image_list
        # # add by zhihao.ding 2015/7/16 for kill_flavor start
        # self.fields['memory_mb'].choices = [
        #                                     ('512',  '512MB'),`
        #                                     ('1024',  '1GB'),
        #                                     ('2048',  '2GB'),
        #                                     ('4096',  '4GB'),
        #                                     ('8192', '8GB'),
        #                                     ('16384',  '16GB'),
        #                                     ('32768', '32GB')]
        # self.fields['vcpus'].choices = [ ('1', '1'),  ('2', '2'),  ('4', '4'), ('8', '8'),  ('16', '16')]
        # self.fields['memory_mb'].initial = '4096'
        # self.fields['vcpus'].initial = '2'
        self.fields['image_type'].widget = forms.widgets.HiddenInput()
        self.fields['instance_snapshot_id'].widget = forms.widgets.HiddenInput()
        self.fields['volume_id'].widget = forms.widgets.HiddenInput()
        self.fields['volume_snapshot_id'].widget = forms.widgets.HiddenInput()
        self.fields['availability_zone'].widget = forms.widgets.HiddenInput()
        # add by zhihao.ding 2015/7/16 for kill_flavor end
    
    # delete by zhihao.ding 2015/7/16 for kill_flavor start
    #@memoized.memoized_method
    #def _get_flavor(self, flavor_id):
    #    try:
    #        # We want to retrieve details for a given flavor,
    #        # however flavor_list uses a memoized decorator
    #        # so it is used instead of flavor_get to reduce the number
    #        # of API calls.
    #        flavors = instance_utils.flavor_list(self.request)
    #        flavor = [x for x in flavors if x.id == flavor_id][0]
    #    except IndexError:
    #        flavor = None
    #    return flavor
    # delete by zhihao.ding 2015/7/16 for kill_flavor end
        
    @memoized.memoized_method
    def _get_image(self, image_id):
        try:
            # We want to retrieve details for a given image,
            # however get_available_images uses a cache of image list,
            # so it is used instead of image_get to reduce the number
            # of API calls.
            images = image_utils.get_available_images(
                self.request,
                self.context.get('project_id'),
                self._images_cache)
            image = [x for x in images if x.id == image_id][0]
        except IndexError:
            image = None
        return image

    # def _check_quotas(self, cleaned_data):
    #     count = cleaned_data.get('count', 1)
    #
    #     # Prevent launching more instances than the quota allows
    #     usages = quotas.tenant_quota_usages(self.request)
    #     available_count = usages['instances']['available']
    #     if available_count < count:
    #         error_message = ungettext_lazy(
    #             'The requested instance cannot be launched as you only '
    #             'have %(avail)i of your quota available. ',
    #             'The requested %(req)i instances cannot be launched as you '
    #             'only have %(avail)i of your quota available.',
    #             count)
    #         params = {'req': count,
    #                   'avail': available_count}
    #         raise forms.ValidationError(error_message % params)
    #
    #     # change by zhihao.ding 2015/7/16 for kill_flavor start
    #     #flavor_id = cleaned_data.get('flavor')
    #     #flavor = self._get_flavor(flavor_id)
    #     vcpus = int(cleaned_data.get('vcpus'))
    #     ram = int(cleaned_data.get('memory_mb'))
    #
    #     count_error = []
    #     # Validate cores and ram.
    #     available_cores = usages['cores']['available']
    #     #if flavor and available_cores < count * flavor.vcpus:
    #     if vcpus and available_cores < count * vcpus:
    #         count_error.append(_("Cores(Available: %(avail)s, "
    #                              "Requested: %(req)s)")
    #                            % {'avail': available_cores,
    #                               'req': count * vcpus})
    #
    #     available_ram = usages['ram']['available']
    #     #if flavor and available_ram < count * flavor.ram:
    #     if ram and available_ram < count * ram:
    #         count_error.append(_("RAM(Available: %(avail)s, "
    #                              "Requested: %(req)s)")
    #                            % {'avail': available_ram,
    #                               'req': count * ram})
    #     # change by zhihao.ding 2015/7/16 for kill_flavor end
    #
    #     if count_error:
    #         value_str = ", ".join(count_error)
    #         msg = (_('The requested instance cannot be launched. '
    #                  'The following requested resource(s) exceed '
    #                  'quota(s): %s.') % value_str)
    #         self._errors['count'] = self.error_class([msg])

    def _check_flavor_for_image(self, cleaned_data):
        # Prevents trying to launch an image needing more resources.
        image_id = cleaned_data.get('selectimage_role_image_id')
        image = self._get_image(image_id)
        # change by zhihao.ding 2015/7/16 for kill_flavor start
        #flavor_id = cleaned_data.get('flavor')
        #flavor = self._get_flavor(flavor_id)
        if not image:# or not flavor:
            return
        '''
        props_mapping = (("min_ram", "ram"), ("min_disk", "disk"))
        for iprop, fprop in props_mapping:
            if getattr(image, iprop) > 0 and getattr(image, iprop) > getattr(flavor, fprop):
                msg = (_("The flavor '%(flavor)s' is too small "
                         "for requested image.\n"
                         "Minimum requirements: "
                         "%(min_ram)s MB of RAM and "
                         "%(min_disk)s GB of Root Disk.") %
                       {'flavor': flavor.name,
                        'min_ram': image.min_ram,
                        'min_disk': image.min_disk})
                self._errors['image_id'] = self.error_class([msg])
                break  # Not necessary to continue the tests.
        '''
        ram = int(cleaned_data.get('memory_mb'))
        if getattr(image, "min_ram") > ram:
            msg = (_("The Memory selected '%(memory_mb)s' is too small "
                         "for requested image.\n"
                         "Minimum requirements: "
                         "%(min_ram)s MB of RAM and "
                         "%(min_disk)s GB of Root Disk.") %
                       {'memory_mb': ram,
                        'min_ram': image.min_ram,
                        'min_disk': image.min_disk})
            self._errors['selectimage_role_image_id'] = self.error_class([msg])
        # change by zhihao.ding 2015/7/16 for kill_flavor end

    def _check_volume_for_image(self, cleaned_data):
        custom_id = cleaned_data.get('custom_image')
        if not custom_id:
            image_id = cleaned_data.get('selectimage_role_image_id')
        else:
            image_id = custom_id
        image = self._get_image(image_id)
        volume_size = cleaned_data.get('volume_size')
        if not image or not volume_size:
            return
        img_gigs = functions.bytes_to_gigabytes(image.size)
        smallest_size = max(img_gigs, image.min_disk)
        cleaned_data['volume_size'] = smallest_size
        '''
        volume_size = cleaned_data.get('volume_size')
        if not image or not volume_size:
            return
        volume_size = int(volume_size)
        img_gigs = functions.bytes_to_gigabytes(image.size)
        smallest_size = max(img_gigs, image.min_disk)
        if volume_size < smallest_size:
            msg = (_("The Volume size is too small for the"
                     " '%(image_name)s' image and has to be"
                     " greater than or equal to "
                     "'%(smallest_size)d' GB.") %
                   {'image_name': image.name,
                    'smallest_size': smallest_size})
            self._errors['volume_size'] = self.error_class([msg])
        '''

    def _check_source_image(self, cleaned_data):
        if not cleaned_data.get('selectimage_role_image_id'):
            msg = _("You must select an image.")
            self._errors['selectimage_role_image_id'] = self.error_class([msg])
        else:
            self._check_flavor_for_image(cleaned_data)

    def _check_source_volume_image(self, cleaned_data):
        volume_size = self.data.get('volume_size', None)
        if not volume_size:
            msg = _("You must set volume size")
            self._errors['volume_size'] = self.error_class([msg])
        if float(volume_size) <= 0:
            msg = _("Volume size must be greater than 0")
            self._errors['volume_size'] = self.error_class([msg])
        if not cleaned_data.get('selectimage_role_image_id') and not cleaned_data.get('custom_image'):
            msg = _("You must select an image.")
            self._errors['selectimage_role_image_id'] = self.error_class([msg])
            return
        else:
            # self._check_flavor_for_image(cleaned_data)
            self._check_volume_for_image(cleaned_data)

    def _check_source_instance_snapshot(self, cleaned_data):
        # using the array form of get blows up with KeyError
        # if instance_snapshot_id is nil
        if not cleaned_data.get('instance_snapshot_id'):
            msg = _("You must select a snapshot.")
            self._errors['instance_snapshot_id'] = self.error_class([msg])

    def _check_source_volume(self, cleaned_data):
        if not cleaned_data.get('volume_id'):
            msg = _("You must select a volume.")
            self._errors['volume_id'] = self.error_class([msg])
        # Prevent launching multiple instances with the same volume.
        # TODO(gabriel): is it safe to launch multiple instances with
        # a snapshot since it should be cloned to new volumes?
        count = cleaned_data.get('count', 1)
        if count > 1:
            msg = _('Launching multiple instances is only supported for '
                    'images and instance snapshots.')
            raise forms.ValidationError(msg)

    def _check_source_volume_snapshot(self, cleaned_data):
        if not cleaned_data.get('volume_snapshot_id'):
            msg = _("You must select a snapshot.")
            self._errors['volume_snapshot_id'] = self.error_class([msg])

    def _check_source(self, cleaned_data):
        # Validate our instance source.
        source_type = self.data.get('image_type', None)
        source_check_methods = {
            'image_id': self._check_source_image,
            'volume_image_id': self._check_source_volume_image,
            'instance_snapshot_id': self._check_source_instance_snapshot,
            'volume_id': self._check_source_volume,
            'volume_snapshot_id': self._check_source_volume_snapshot
        }
        check_method = source_check_methods.get(source_type)
        if check_method:
            check_method(cleaned_data)

    def clean(self):
        cleaned_data = super(SelectImageAction, self).clean()
        # self._check_quotas(cleaned_data)
        self._check_source(cleaned_data)
        return cleaned_data
    
    # delete by zhihao.ding 2015/7/16 for kill_flavor start
    #def populate_flavor_choices(self, request, context):
    #    return instance_utils.flavor_field_data(request, False)
    # delete by zhihao.ding 2015/7/16 for kill_flavor end

    def populate_availability_zone_choices(self, request, context):
        try:
            zones = api.nova.availability_zone_list(request)
        except Exception:
            zones = []
            exceptions.handle(request,
                              _('Unable to retrieve availability zones.'))

        zone_list = [(zone.zoneName, zone.zoneName)
                     for zone in zones if zone.zoneState['available']]
        zone_list.sort()
        if not zone_list:
            zone_list.insert(0, ("", _("No availability zones found")))
        elif len(zone_list) > 1:
            zone_list.insert(0, ("", _("Any Availability Zone")))
        return zone_list

    def get_help_text(self, extra_context=None):
        extra = {} if extra_context is None else dict(extra_context)
        try:
            extra['usages'] = api.nova.tenant_absolute_limits(self.request)
            extra['usages_json'] = json.dumps(extra['usages'])
            # delete by zhihao.ding 2015/7/16 for kill_flavor start
            #flavors = json.dumps([f._info for f in instance_utils.flavor_list(self.request)])
            #extra['flavors'] = flavors
            # delete by zhihao.ding 2015/7/16 for kill_flavor start
            images = image_utils.get_available_images(
                self.request, self.initial['project_id'], self._images_cache)
            if images is not None:
                attrs = [{'id': i.id,
                          'min_disk': getattr(i, 'min_disk', 0),
                          'min_ram': getattr(i, 'min_ram', 0),
                          'size': functions.bytes_to_gigabytes(i.size)}
                         for i in images]
                extra['images'] = json.dumps(attrs)

        except Exception:
            exceptions.handle(self.request,
                              _("Unable to retrieve quota information."))
        return super(SelectImageAction, self).get_help_text(extra)

    def _init_images_cache(self):
        if not hasattr(self, '_images_cache'):
            self._images_cache = {}

    def _get_volume_display_name(self, volume):
        if hasattr(volume, "volume_id"):
            vol_type = "snap"
            visible_label = _("Snapshot")
        else:
            vol_type = "vol"
            visible_label = _("Volume")
        return (("%s:%s" % (volume.id, vol_type)),
                (_("%(name)s - %(size)s GB (%(label)s)") %
                 {'name': volume.name,
                  'size': volume.size,
                  'label': visible_label}))

    def populate_image_id_choices(self, request, context):
        choices = []
        images = image_utils.get_available_images(request,
                                                  context.get('project_id'),
                                                  self._images_cache)
        for image in images:
            image.bytes = image.virtual_size or image.size
            image.volume_size = max(
                image.min_disk, functions.bytes_to_gigabytes(image.bytes))
            choices.append((image.id, image))
            if context.get('selectimage_role_image_id') == image.id and \
                    context.get('image_type') == 'volume_image_id':
                context['volume_size'] = image.volume_size
        if choices:
            choices.sort(key=lambda c: c[1].name)
            choices.insert(0, ("", _("Select Image")))
        else:
            choices.insert(0, ("", _("No images available")))
        return choices

    # def populate_instance_snapshot_id_choices(self, request, context):
    #     images = image_utils.get_available_images(request,
    #                                               context.get('project_id'),
    #                                               self._images_cache)
    #     choices = [(image.id, image.name)
    #                for image in images
    #                if image.properties.get("image_type", '') == "snapshot"]
    #     if choices:
    #         choices.sort(key=operator.itemgetter(1))
    #         choices.insert(0, ("", _("Select Instance Snapshot")))
    #     else:
    #         choices.insert(0, ("", _("No snapshots available")))
    #     return choices
    #
    # def populate_volume_id_choices(self, request, context):
    #     volumes = []
    #     try:
    #         if base.is_service_enabled(request, 'volume'):
    #             available = api.cinder.VOLUME_STATE_AVAILABLE
    #             volumes = [self._get_volume_display_name(v)
    #                        for v in cinder.volume_list(self.request,
    #                        search_opts=dict(status=available, bootable=1))]
    #     except Exception:
    #         exceptions.handle(self.request,
    #                           _('Unable to retrieve list of volumes.'))
    #     if volumes:
    #         volumes.insert(0, ("", _("Select Volume")))
    #     else:
    #         volumes.insert(0, ("", _("No volumes available")))
    #     return volumes
    #
    # def populate_volume_snapshot_id_choices(self, request, context):
    #     snapshots = []
    #     try:
    #         if base.is_service_enabled(request, 'volume'):
    #             available = api.cinder.VOLUME_STATE_AVAILABLE
    #             snapshots = [self._get_volume_display_name(s)
    #                          for s in cinder.volume_snapshot_list(
    #                          self.request, search_opts=dict(status=available))]
    #     except Exception:
    #         exceptions.handle(self.request,
    #                           _('Unable to retrieve list of volume '
    #                             'snapshots.'))
    #     if snapshots:
    #         snapshots.insert(0, ("", _("Select Volume Snapshot")))
    #     else:
    #         snapshots.insert(0, ("", _("No volume snapshots available")))
    #     return snapshots


class SelectImage(workflows.UpdateMembersStep):
    action_class = SelectImageAction
    available_list_title = _("All Images")
    members_list_title = _("Selected Image")
    no_available_text = _("No images found.")
    no_members_text = _("No images.")
    template_name = "instances/instances/_workflow_step_update_images.html"
    depends_on = ("project_id", "user_id")
    contributes = ("image_type", "selectimage_role_default",
                   "availability_zone", "flavor", "instance_snapshot_id"
                   "device_name", 'selectimage_role_image_id', 'custom_image'  # Can be None for an image.
                   )
    show_roles = False
    step = 1

    def prepare_action_context(self, request, context):
        if 'image_type' in context and context[context['image_type']] not in context:
            context[context['source_type']] = context['source_id']
        else:
            context['image_type'] = 'volume_image_id'
        return context

    def contribute(self, data, context):
        context = super(SelectImage, self).contribute(data, context)
        # Allow setting the source dynamically.

        if ("source_type" in context and context['source_id']
                and context["source_type"] not in context):
            context[context["source_type"]] = context["source_id"]

        # Translate form input to context for source values.

        if "source_type" in data:
                context["source_type"] = data.get('source_type', None)

        if "volume_size" in data:
            context["volume_size"] = data["volume_size"]

        return context

# KEYPAIR_IMPORT_URL = "horizon:security:keypairs:import"

level_choice = [
    ('keypair', _("Keypair")),
    ('password', _("Password"))]


class BaseInfoAction(workflows.Action):
    name = forms.CharField(label=_("Instance Name"),
                           max_length=255)
    count = forms.IntegerField(label=_("Instance Count"),
                               min_value=1,
                               initial=1,
                               help_text=_("Number of instances to launch."))
    username = forms.CharField(max_length=64, label=_("User Name"), required=True)
                               #widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    sync_set_root = forms.BooleanField(label=_("Sync set root/Administrator password"), initial=True, required=False)
    keypair = forms.ChoiceField(label=_("Key Pair"), required=False,
                                help_text=_("Key pair to use for "
                                                   "authentication."))
    admin_pass = forms.RegexField(
        label=_("Password"),
        required=False,
        widget=forms.PasswordInput(render_value=False, attrs={'placeholder': _('begin letter,8-64 bits,with number,letter and symbol')}),
        regex=validators.password_validator(),
        error_messages={'invalid': validators.password_validator_msg()})
    confirm_admin_pass = forms.CharField(
        label=_("Confirm Password"),
        required=False,
        widget=forms.PasswordInput(render_value=False))
    # groups = forms.MultipleChoiceField(label=_("Security Groups"),
    #                                    required=False,
    #                                    initial=["default"],
    #                                    widget=forms.CheckboxSelectMultiple(),
    #                                    help_text=_("Launch instance in these "
    #                                                "security groups."))
    source_choices = [('', _('Select Script Source')),
                      ('raw', _('Direct Input')),
                      ('file', _('File'))]

    attributes = {'class': 'switchable', 'data-slug': 'scriptsource'}
    script_source = forms.ChoiceField(label=_('Customization Script Source'),
                                      choices=source_choices,
                                      widget=forms.Select(attrs=attributes),
                                      required=False)

    script_help = _("A script or set of commands to be executed after the "
                    "instance has been built (max 16kb).")

    script_upload = forms.FileField(
        label=_('Script File'),
        # help_text=script_help,
        widget=forms.FileInput(attrs={
            'class': 'switched',
            'data-switch-on': 'scriptsource',
            'data-scriptsource-file': _('Script File')}),
        required=False)

    script_data = forms.CharField(
        label=_('Script Data'),
        # help_text=script_help,
        widget=forms.widgets.Textarea(attrs={
            'class': 'switched',
            'data-switch-on': 'scriptsource',
            'data-scriptsource-raw': _('Script Data')}),
        required=False)

    class Meta(object):
        name = _("Base Info")
        slug = 'baseinfo'

    def __init__(self, request, *args, **kwargs):
        super(BaseInfoAction, self).__init__(request, *args, **kwargs)
        self.fields["username"].initial = 'syscloud'
        self.is_allow_inject_passwd = False
        source_type = args[0].get('source_type', None)
        select_image_id = None
        if (source_type != None) and (source_type not in ['volume_snapshot_id', 'volume_id']):
            if source_type == "":
                select_image_id = args[0].get('selectimage_role_image_id', None)
                if select_image_id == "":
                    select_image_id = args[0].get('custom_image', None)
            else:
                select_image_id = args[0].get('source_id', None)
        if select_image_id:
            image = api.glance.image_get(request, select_image_id)
            self.is_allow_inject_passwd = getattr(image, 'is_allow_inject_passwd', False)

        if not api.nova.can_set_server_password():
            del self.fields['admin_pass']

    def populate_keypair_choices(self, request, context):
        keypairs = instance_utils.keypair_field_data(request, True)
        if len(keypairs) == 2:
            self.fields['keypair'].initial = keypairs[1][0]
        return keypairs

    def populate_groups_choices(self, request, context):
        try:
            groups = api.network.security_group_list(request)
            security_group_list = [(sg.name, sg.name) for sg in groups]
        except Exception:
            exceptions.handle(request,
                              _('Unable to retrieve list of security groups'))
            security_group_list = []
        return security_group_list

    def clean(self):
        '''Check to make sure password fields match.'''
        cleaned_data = super(BaseInfoAction, self).clean()
        files = self.request.FILES
        script = self.clean_uploaded_files('script', files)
        if script is not None:
            cleaned_data['script_data'] = script
        if 'admin_pass' in cleaned_data:
            if cleaned_data['admin_pass'] != cleaned_data.get(
                    'confirm_admin_pass', None):
                raise forms.ValidationError(_('Passwords do not match.'))
            if self.is_allow_inject_passwd:
                if not validators.validate_password(cleaned_data['admin_pass']):
                    raise forms.ValidationError(_("The password must begin with a letter, "
                                                  "and the length is between the 8-64 bits, "
                                                  "and the number, the letter and the symbol are the same.")) 
        return cleaned_data

    def clean_uploaded_files(self, prefix, files):
        upload_str = prefix + "_upload"

        has_upload = upload_str in files
        if has_upload:
            upload_file = files[upload_str]
            log_script_name = upload_file.name
            LOG.info('got upload %s' % log_script_name)

            if upload_file._size > 16 * units.Ki:  # 16kb
                msg = _('File exceeds maximum size (16kb)')
                raise forms.ValidationError(msg)
            else:
                script = upload_file.read()
                if script != "":
                    try:
                        normalize_newlines(script)
                    except Exception as e:
                        msg = _('There was a problem parsing the'
                                ' %(prefix)s: %(error)s')
                        msg = msg % {'prefix': prefix, 'error': e}
                        raise forms.ValidationError(msg)
                return script
        else:
            return None


class BaseInfo(workflows.Step):
    action_class = BaseInfoAction
    depends_on = ("project_id", "user_id")
    contributes = ("name", "count", "keypair_id", "security_group_ids", "username", "sync_set_root",
                   "admin_pass", "confirm_admin_pass")
    template_name = "instances/instances/_workflow_step.html"
    step = 3

    def contribute(self, data, context):
        if data:
            post = self.workflow.request.POST
            context['name'] = data.get("name", "")
            context['count'] = data.get("count", 1)
            context['security_group_ids'] = post.getlist("groups")
            context['keypair_id'] = data.get("keypair", "")
            context['username'] = data.get('username', 'syscloud')
            context['sync_set_root'] = data.get('sync_set_root', True)
            context['admin_pass'] = data.get("admin_pass", "")
            context['confirm_admin_pass'] = data.get("confirm_admin_pass", "")
        return context


class CustomizeAction(workflows.Action):
    class Meta(object):
        name = _("Post-Creation")
        help_text_template = ("instances/instances/"
                              "_launch_details_help.html")

    source_choices = [('', _('Select Script Source')),
                      ('raw', _('Direct Input')),
                      ('file', _('File'))]

    attributes = {'class': 'switchable', 'data-slug': 'scriptsource'}
    script_source = forms.ChoiceField(label=_('Customization Script Source'),
                                      choices=source_choices,
                                      widget=forms.Select(attrs=attributes),
                                      required=False)

    script_help = _("A script or set of commands to be executed after the "
                    "instance has been built (max 16kb).")

    script_upload = forms.FileField(
        label=_('Script File'),
        help_text=script_help,
        widget=forms.FileInput(attrs={
            'class': 'switched',
            'data-switch-on': 'scriptsource',
            'data-scriptsource-file': _('Script File')}),
        required=False)

    script_data = forms.CharField(
        label=_('Script Data'),
        help_text=script_help,
        widget=forms.widgets.Textarea(attrs={
            'class': 'switched',
            'data-switch-on': 'scriptsource',
            'data-scriptsource-raw': _('Script Data')}),
        required=False)

    def __init__(self, *args):
        super(CustomizeAction, self).__init__(*args)

    def clean(self):
        cleaned = super(CustomizeAction, self).clean()

        files = self.request.FILES
        script = self.clean_uploaded_files('script', files)

        if script is not None:
            cleaned['script_data'] = script

        return cleaned

    def clean_uploaded_files(self, prefix, files):
        upload_str = prefix + "_upload"

        has_upload = upload_str in files
        if has_upload:
            upload_file = files[upload_str]
            log_script_name = upload_file.name
            LOG.info('got upload %s' % log_script_name)

            if upload_file._size > 16 * units.Ki:  # 16kb
                msg = _('File exceeds maximum size (16kb)')
                raise forms.ValidationError(msg)
            else:
                script = upload_file.read()
                if script != "":
                    try:
                        normalize_newlines(script)
                    except Exception as e:
                        msg = _('There was a problem parsing the'
                                ' %(prefix)s: %(error)s')
                        msg = msg % {'prefix': prefix, 'error': e}
                        raise forms.ValidationError(msg)
                return script
        else:
            return None


class PostCreationStep(workflows.Step):
    action_class = CustomizeAction
    contributes = ("script_data",)


class SelectConfigAction(workflows.Action):
    vcpus = forms.ChoiceField(label='', required=False,
                              widget=forms.SelectWidget(attrs={'class': 'select_cpu'}))
    memory_mb = forms.ChoiceField(label='', required=False,
                                  widget=forms.SelectWidget(attrs={'class': 'select_mem'}))
    cloud_hdd = forms.IntegerField(label='', min_value=0, widget=forms.TextInput(attrs={'class': 'select_hdd'}),
                                   required=False)
    network = forms.ChoiceField(label=_("Networks"),
                                widget=forms.SelectWidget(),
                                error_messages={
                                            'required': _(
                                                "At least one network must"
                                                " be specified.")},
                                help_text=_("Launch instance with"
                                                    " these networks"))
    is_create_floating_ip = forms.BooleanField(label=_("If Float IP"), required=False)
    floating_ip_limit_speed = forms.IntegerField(label=_("IO Top(Mbps)"), required=False,
                                     min_value=-1, initial=-1,
                                     help_text=_("Should little than Total Bandwidth, Set -1 or 0 If want have no limit."))
    if api.neutron.is_port_profiles_supported():
        widget = None
    else:
        widget = forms.HiddenInput()
    profile = forms.ChoiceField(label=_("Policy Profiles"),
                                required=False,
                                widget=widget,
                                help_text=_("Launch instance with "
                                            "this policy profile"))
    source_type = forms.CharField(label=None, widget=forms.TextInput(), required=False)
    source_id = forms.CharField(label=None, widget=forms.TextInput(), required=False)
    image_name = forms.CharField(label=None, widget=forms.TextInput(), required=False)
    image_size = forms.CharField(label=None, widget=forms.TextInput(), required=False)

    def __init__(self, request, context, *args, **kwargs):
        self._init_images_cache()
        self.request = request
        self.context = context
        super(SelectConfigAction, self).__init__(request, context, *args, **kwargs)
        network_list = self.fields["network"].choices
        self.fields['memory_mb'].choices = horizon_units.get_memory_choices(SHOW_MIN_CHOICES_FOR_TEST)
        self.fields['vcpus'].choices = horizon_units.get_vcpus_choices(SHOW_MIN_CHOICES_FOR_TEST)
        self.fields['memory_mb'].initial = '4096'
        self.fields['vcpus'].initial = '2'
        if len(network_list) == 1:
            self.fields['network'].initial = [network_list[0][0]]
        if api.neutron.is_port_profiles_supported():
            self.fields['profile'].choices = (
                self.get_policy_profile_choices(request))

        source_type = request.GET.get("source_type", None)
        source_id = request.GET.get("source_id", None)
        if not source_type:
            self.fields['image_name'].widget = forms.widgets.HiddenInput()
        else:
            if source_type == 'image_id':
                image = api.glance.image_get(request, source_id)
                self.fields['image_name'].label = _('Image Name')
                self.fields['image_name'].initial = image.name
                self.fields['image_name'].widget = forms.TextInput(attrs={'size': image.min_disk, 'is_allow_inject_passwd':
                                                                   str(1 if getattr(image, 'is_allow_inject_passwd', False) else 0)})
                context['source_type'] = 'image_id'
                context[context['source_type']] = source_id
            elif source_type == 'volume_id':
                source_id = source_id.split(":")[0]
                volume = cinder.volume_get(request, source_id)
                self.fields['image_name'].label = _('Volume Name')
                self.fields['image_name'].initial = volume.name
                self.fields['image_name'].widget = forms.TextInput(attrs={'size': volume.size, 'is_allow_inject_passwd': '0'})
                context['source_type'] = 'volume_id'
                context[context['source_type']] = source_id
            else:
                source_id = source_id.split(":")[0]
                snap = api.cinder.volume_snapshot_get(request, source_id)
                self.fields['image_name'].label = _('Volume Snap Name')
                self.fields['image_name'].initial = snap.name
                self.fields['image_name'].widget = forms.TextInput(attrs={'size': snap.size, 'is_allow_inject_passwd': '0'})
                context['source_type'] = 'volume_snapshot_id'
                context[context['source_type']] = source_id



    class Meta(object):
        name = _("Select Config")
        slug = 'selectconfig'
        permissions = ('openstack.services.network',)

    def _init_images_cache(self):
        if not hasattr(self, '_images_cache'):
            self._images_cache = {}

    def populate_network_choices(self, request, context):
        return instance_utils.network_field_data(request)

    def get_policy_profile_choices(self, request):
        profile_choices = [('', _("Select a profile"))]
        for profile in self._get_profiles(request, 'policy'):
            profile_choices.append((profile.id, profile.name))
        return profile_choices

    def _get_profiles(self, request, type_p):
        profiles = []
        try:
            profiles = api.neutron.profile_list(request, type_p)
        except Exception:
            msg = _('Network Profiles could not be retrieved.')
            exceptions.handle(request, msg)
        return profiles

    def _check_quotas(self, cleaned_data):
        count = cleaned_data.get('count', 1)
        # Prevent launching more instances than the quota allows
        usages = quotas.tenant_quota_usages(self.request)

        # check float ip  quota

        # available_float_ip = usages['floating_ips']['available']
        # if available_float_ip <= 0:
        #         error_message = _('You are already using all of your available'
        #                           ' floating IPs.')
        #         self._errors['float_ip'] = self.error_class([error_message])

        # check data hdd quota
        # hdd_usages = quotas.tenant_limit_usages(self.request)
        # availableGB = hdd_usages['maxTotalVolumeGigabytes'] - hdd_usages['gigabytesUsed']
        # availableVol = hdd_usages['maxTotalVolumes'] - hdd_usages['volumesUsed']
        # if availableGB < cleaned_data['cloud_hdd']:
        #     error_message = _('A volume of %(req)iGB cannot be created as '
        #                       'you only have %(avail)iGB of your quota '
        #                       'available.')
        #     params = {'req': cleaned_data['cloud_hdd'], 'avail': availableGB}
        #     raise ValidationError(error_message % params)
        # elif availableVol <= 0:
        #     error_message = _('You are already using all of your available volumes.')
        #     raise ValidationError(error_message)


        available_count = usages['instances']['available']
        if available_count < count:
            error_message = ungettext_lazy(
                'The requested instance cannot be launched as you only '
                'have %(avail)i of your quota available. ',
                'The requested %(req)i instances cannot be launched as you '
                'only have %(avail)i of your quota available.',
                count)
            params = {'req': count,
                      'avail': available_count}
            raise forms.ValidationError(error_message % params)

        # change by zhihao.ding 2015/7/16 for kill_flavor start
        #flavor_id = cleaned_data.get('flavor')
        #flavor = self._get_flavor(flavor_id)
        vcpus = int(cleaned_data.get('vcpus'))
        ram = int(cleaned_data.get('memory_mb'))

        count_error = []
        # Validate cores and ram.
        available_cores = usages['cores']['available']
        #if flavor and available_cores < count * flavor.vcpus:
        if vcpus and available_cores < count * vcpus:
            count_error.append(_("Cores(Available: %(avail)s, "
                                 "Requested: %(req)s)")
                               % {'avail': available_cores,
                                  'req': count * vcpus})

        available_ram = usages['ram']['available']
        #if flavor and available_ram < count * flavor.ram:
        if ram and available_ram < count * ram:
            count_error.append(_("RAM(Available: %(avail)s, "
                                 "Requested: %(req)s)")
                               % {'avail': available_ram,
                                  'req': count * ram})
        # change by zhihao.ding 2015/7/16 for kill_flavor end

        if count_error:
            value_str = ", ".join(count_error)
            msg = (_('The requested instance cannot be launched. '
                     'The following requested resource(s) exceed '
                     'quota(s): %s.') % value_str)
            self._errors['count'] = self.error_class([msg])

        # create from image /get volume size
        if cleaned_data.get('source_type') == 'image_id':
            image_id = cleaned_data.get('source_id')
            image = self._get_image(image_id)
            img_gigs = functions.bytes_to_gigabytes(image.size)
            smallest_size = max(img_gigs, image.min_disk)
            cleaned_data['image_size'] = smallest_size

    @memoized.memoized_method
    def _get_image(self, image_id):
        try:
            # We want to retrieve details for a given image,
            # however get_available_images uses a cache of image list,
            # so it is used instead of image_get to reduce the number
            # of API calls.
            images = image_utils.get_available_images(
                self.request,
                self.context.get('project_id'),
                self._images_cache)
            image = [x for x in images if x.id == image_id][0]
        except IndexError:
            image = None
        return image

    def clean(self):
        cleaned_data = super(SelectConfigAction, self).clean()
        self._check_quotas(cleaned_data)
        return cleaned_data


class SelectConfig(workflows.Step):
    action_class = SelectConfigAction
    depends_on = ("project_id", "user_id")
    contributes = ('vcpus', 'memory_mb', "cloud_hdd", "is_create_floating_ip",
                   "floating_ip_limit_speed", 'image_name', "source_type", "source_id", "image_size")
    template_name = "instances/instances/_workflow_step.html"
    step = 2
    # Disabling the template drag/drop only in the case port profiles
    # are used till the issue with the drag/drop affecting the
    # profile_id detection is fixed.
    if api.neutron.is_port_profiles_supported():
        contributes = contributes+("network_id", "profile_id",)
    else:
        # template_name = "instances/instances/_update_networks.html"
        contributes = contributes+("network_id",)

    def contribute(self, data, context):
        context = super(SelectConfig, self).contribute(data, context)
        if data:
            networks = self.workflow.request.POST.getlist("network")
            # If no networks are explicitly specified, network list
            # contains an empty string, so remove it.
            networks = [n for n in networks if n != '']
            if networks:
                context['network_id'] = networks

            if api.neutron.is_port_profiles_supported():
                context['profile_id'] = data.get('profile', None)
            if "image_size" in data:
                context["image_size"] = data["image_size"]
        return context


class SetAdvancedAction(workflows.Action):
    disk_config = forms.ChoiceField(
        label=_("Disk Partition"), required=False,
        help_text=_("Automatic: The entire disk is a single partition and "
                    "automatically resizes. Manual: Results in faster build "
                    "times but requires manual partitioning."))
    config_drive = forms.BooleanField(
        label=_("Configuration Drive"),
        required=False, help_text=_("Configure OpenStack to write metadata to "
                                    "a special configuration drive that "
                                    "attaches to the instance when it boots."))

    def __init__(self, request, context, *args, **kwargs):
        super(SetAdvancedAction, self).__init__(request, context,
                                                *args, **kwargs)
        try:
            if not api.nova.extension_supported("DiskConfig", request):
                del self.fields['disk_config']
            else:
                # Set our disk_config choices
                config_choices = [("AUTO", _("Automatic")),
                                  ("MANUAL", _("Manual"))]
                self.fields['disk_config'].choices = config_choices
            # Only show the Config Drive option for the Launch Instance
            # workflow (not Resize Instance) and only if the extension
            # is supported.
            if context.get('workflow_slug') != 'launch_instance' or (
                    not api.nova.extension_supported("ConfigDrive", request)):
                del self.fields['config_drive']
        except Exception:
            exceptions.handle(request, _('Unable to retrieve extensions '
                                         'information.'))

    class Meta(object):
        name = _("Advanced Options")
        slug = "instance_advanced_options"
        help_text_template = ("instances/instances/"
                              "_launch_details_help.html")


class SetAdvanced(workflows.Step):
    action_class = SetAdvancedAction
    contributes = ("disk_config", "config_drive",)

    def prepare_action_context(self, request, context):
        context = super(SetAdvanced, self).prepare_action_context(request,
                                                                  context)
        # Add the workflow slug to the context so that we can tell which
        # workflow is being used when creating the action. This step is
        # used by both the Launch Instance and Resize Instance workflows.
        context['workflow_slug'] = self.workflow.slug
        return context

class LaunchInstanceHandleHelper:

    def _get_image_name(self, request, context):
        image_name = None
        source_type = context.get('source_type', None)
        select_image_id = None
        if (source_type != None) and (source_type not in ['volume_snapshot_id', 'volume_id']):
            if source_type == "":
                select_image_id = context.get('selectimage_role_image_id', None)
                if select_image_id  == "":
                        select_image_id = context.get('custom_image', None)
            else:
                select_image_id = context.get('source_id', None)
        if select_image_id:
            image = api.glance.image_get(request, select_image_id)
            image_name = getattr(image, 'name', False)
        return image_name

    def _set_user_data(self, request, context):
        custom_script = context.get('script_data', '')
        admin_pass = context.get('admin_pass', None)
        if admin_pass:
            image_name = self._get_image_name(request, context)
            is_create_data_volume = True if context.get("cloud_hdd", 0) > 0 else False
            username = context.get('username', 'syscloud')
            is_sync_set_root = context.get('sync_set_root', False)
            user_data_script_helper = userdata.UserDataScriptHelper(image_name, is_create_data_volume, is_sync_set_root)
            custom_script = user_data_script_helper.get_user_data(username, admin_pass)
        return custom_script

    def set_network_port_profiles(self, request, net_ids, profile_id):
        # Create port with Network ID and Port Profile
        # for the use with the plugin supporting port profiles.
        nics = []
        for net_id in net_ids:
            try:
                port = api.neutron.port_create(
                    request,
                    net_id,
                    policy_profile_id=profile_id,
                )
            except Exception as e:
                msg = (_('Unable to create port for profile '
                         '"%(profile_id)s": %(reason)s'),
                       {'profile_id': profile_id,
                        'reason': e})
                for nic in nics:
                    try:
                        port_id = nic['port-id']
                        api.neutron.port_delete(request, port_id)
                    except Exception:
                        msg = (msg +
                               _(' Also failed to delete port %s') % port_id)
                redirect = self.success_url
                exceptions.handle(request, msg, redirect=redirect)

            if port:
                nics.append({"port-id": port.id})
                LOG.debug("Created Port %(portid)s with "
                          "network %(netid)s "
                          "policy profile %(profile_id)s",
                          {'portid': port.id,
                           'netid': net_id,
                           'profile_id': profile_id})

        return nics

    def _create_data_volumes(self, request, context):
        cloud_hdd = context.get("cloud_hdd", 0)
        is_create_data_volume = True if cloud_hdd > 0 else False
        data_volume_id = None
        data_volumes = []
        volumes_size = []
        try:
            if is_create_data_volume:
                instance_count = int(context['count'])
                for i in xrange(instance_count):
                    volume = cinder.volume_create(request, cloud_hdd, '', '', '')
                    data_volume_id = getattr(volume, "id", None)
                    size = getattr(volume, "size", None)
                    if data_volume_id:
                        data_volumes.append(data_volume_id)
                        volumes_size.append(size)
        except Exception:
            exceptions.handle(request)
        return (is_create_data_volume, data_volumes, volumes_size)

    def _destory_data_volumes(self, request, data_volumes):
        try:
            if data_volumes:
                for data_volume_id in data_volumes:
                    cinder.volume_delete(request, data_volume_id)
        except Exception:
            exceptions.handle(request)

    def _create_floating_ips(self, request, context):
        is_create_floating_ip = context.get("is_create_floating_ip", False)
        floating_ip_limit_speed = context.get("floating_ip_limit_speed", -1)
        floating_ip_id = None
        floating_ips = []
        ips = []
        try:
            if is_create_floating_ip:
                instance_count = int(context['count'])
                for i in xrange(instance_count):
                    pools = api.network.floating_ip_pools_list(request)
                    pool_list = [pool.id for pool in pools]
                    fip = api.network.tenant_floating_ip_allocate(request, pool_list[0], floating_ip_limit_speed)
                    floating_ip_id = getattr(fip, "id", None)
                    ip = getattr(fip, "ip", None)
                    if floating_ip_id:
                        floating_ips.append(floating_ip_id)
                        ips.append(str(ip))
        except Exception:
            exceptions.handle(request)
        return (is_create_floating_ip, floating_ips, ips)

    def _destory_floating_ips(self, request, floating_ips):
        try:
            if floating_ips:
                for floating_ip_id in floating_ips:
                    api.network.tenant_floating_ip_release(request, floating_ip_id)
        except Exception:
            exceptions.handle(request)

    def _create_instance(self, request, context, custom_script,
                         is_create_floating_ip, floating_ips, ips,
                         is_create_data_volume, data_volumes, volumes_size):
        while True:
            if is_create_floating_ip and floating_ips is None:
                break;
            if is_create_data_volume and data_volumes is None:
                break;

            dev_mapping_1 = None
            dev_mapping_2 = None
            image_id = ''

            source_type = context.get('source_type', None)
            select_image_id = None
            volume_size = None
            if source_type is None:
                pass
            elif source_type in ['volume_id', 'volume_snapshot_id']:
                select_image_id = context['source_id']
                device_name = context.get('device_name', 'vda').strip() or None
                dev_mapping_1 = {device_name:
                                 '%s::%s' %
                                 (select_image_id, 0)}
            else:
                if source_type == "":
                    select_image_id = context.get('selectimage_role_image_id', None)
                    volume_size = context['volume_size']
                    if select_image_id  == "":
                        select_image_id = context.get('custom_image', None)
                else:
                    select_image_id = context.get('source_id', None)
                    volume_size = context['image_size']

                image_id = select_image_id

                device_name = context.get('device_name', '').strip() or None
                dev_mapping_2 = [
                    {'device_name': device_name,  # None auto-selects device
                     'source_type': 'image',
                     'destination_type': 'volume',
                     'delete_on_termination': 0,
                     'uuid': select_image_id,
                     'boot_index': '0',
                     'volume_size': volume_size}]

            netids = context.get('network_id', None)
            if netids:
                nics = [{"net-id": netid, "v4-fixed-ip": ""}
                        for netid in netids]
            else:
                nics = None

            avail_zone = context.get('availability_zone', None)

            if api.neutron.is_port_profiles_supported():
                nics = self.set_network_port_profiles(request,
                                                      context['network_id'],
                                                      context['profile_id'])

            meta = {}
            meta['memory_mb'] = context['memory_mb']
            meta['vcpus'] = context['vcpus']
            if data_volumes:
                meta['data_volumes'] = str(data_volumes)
            if floating_ips:
                meta['floating_ips'] = str(floating_ips)

            flavors = instance_utils.flavor_field_data(request, False)
            flavor = str(flavors[0][0])

            # operation log
            resource_type = None
            resource_name = None

            if source_type =='volume_id':
                resource_type = 'volume'
                resource_name = 'Volume'
            elif source_type == 'volume_snapshot_id':
                resource_type = 'snapshot'
                resource_name = 'Snapshot'
            elif source_type == 'image_id':
                resource_type = 'image'
                resource_name = 'Image'
            else:
                resource_type = 'instance'
                resource_name = 'Instance'

            try:
                api.nova.server_create(request,
                                       context['name'],
                                       image_id,
                                       flavor,
                                       context['keypair_id'],
                                       normalize_newlines(custom_script),
                                       context['security_group_ids'],
                                       block_device_mapping=dev_mapping_1,
                                       block_device_mapping_v2=dev_mapping_2,
                                       nics=nics,
                                       availability_zone=avail_zone,
                                       instance_count=int(context['count']),
                                       admin_pass=context['admin_pass'],
                                       disk_config=context.get('disk_config'),
                                       config_drive=context.get('config_drive'),
                                       meta=meta)

                # operation log
                config = _('Instance Name: %s Count: %d CPU: %s Memory: %sMB Float IP: %s  Volume: %s') % (context['name'],
                                                                                                      context['count'],
                                                                                                      str(context['vcpus']),
                                                                                                      str(context['memory_mb']),
                                                                                                      str(ips),
                                                                                                      str(volumes_size))


                api.logger.Logger(request).create(resource_type=resource_type, action_name='Create Instance',
                                                       resource_name=resource_name, config=config,
                                                       status='Success')
            except Exception:
                # operation log
                exceptions.handle(request)
                api.logger.Logger(request).create(resource_type=resource_type, action_name='Create Instance',
                                                       resource_name=resource_name, config='',
                                                       status='Error')
                break;

            return True

        self._destory_floating_ips(request, floating_ips)
        self._destory_data_volumes(request, data_volumes)
        return False

    def handle(self, request, context):
        # create user_data
        custom_script = self._set_user_data(request, context)
        # create floating IP if need
        is_create_floating_ip, floating_ips, ips = self._create_floating_ips(request, context)
        # create data volume if need
        is_create_data_volume, data_volumes, volumes_size = self._create_data_volumes(request, context)
        # create instance last
        return self._create_instance(request,
                                     context,
                                     custom_script,
                                     is_create_floating_ip,
                                     floating_ips, ips,
                                     is_create_data_volume,
                                     data_volumes, volumes_size)


class LaunchInstance(workflows.Workflow):
    slug = "launch_instance"
    name = _("Launch Instance")
    finalize_button_name = _("Launch")
    success_message = _('Launched %(count)s named "%(name)s".')
    failure_message = _('Unable to launch %(count)s named "%(name)s".')
    success_url = "horizon:instances:instances:index"
    multipart = True
    wizard = True
    selectimage = True
    default_steps = (SelectProjectUser,
                     SelectImage,
                     SelectConfig,
                     BaseInfo,
                     )

    def format_status_message(self, message):
        name = self.context.get('name', 'unknown instance')
        count = self.context.get('count', 1)
        if int(count) > 1:
            return message % {"count": _("%s instances") % count,
                              "name": name}
        else:
            return message % {"count": _("instance"), "name": name}

    @sensitive_variables('context')
    def handle(self, request, context):
        handle_helper = LaunchInstanceHandleHelper()
        return handle_helper.handle(request, context)

class LaunchInstanceIsv(LaunchInstance):
    selectimage = False
    default_steps = (SelectProjectUser,
                     SelectConfig,
                     BaseInfo,
                     )
