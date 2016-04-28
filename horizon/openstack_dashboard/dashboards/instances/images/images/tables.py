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

from collections import defaultdict

from django.conf import settings
from django.core.urlresolvers import reverse
from django.template import defaultfilters as filters
from django.utils.http import urlencode
from django.utils.translation import pgettext_lazy
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext_lazy

from horizon import tables
from horizon.utils.memoized import memoized  # noqa
from horizon.utils.functions import check_account_is_frozen

from openstack_dashboard import api
from openstack_dashboard.api import base
from horizon.utils import filters as horizon_filters


NOT_LAUNCHABLE_FORMATS = ['aki', 'ari']


class LaunchImage(tables.LinkAction):
    name = "launch_image"
    verbose_name = _("Launch Instance")
    url = "horizon:instances:instances:launchISV"
    classes = ("ajax-modal", "btn-launch")
    icon = "cloud-upload"
    policy_rules = (("compute", "compute:create"),)

    def get_link_url(self, datum):
        base_url = reverse(self.url)

        if get_image_type(datum) == "image":
            source_type = "image_id"
        else:
            source_type = "instance_snapshot_id"

        params = urlencode({"source_type": source_type,
                            "source_id": self.table.get_object_id(datum)})
        return "?".join([base_url, params])

    def allowed(self, request, image=None):
        account_is_frozen = check_account_is_frozen(request)
        if account_is_frozen:
            if "disabled" not in self.classes:
                self.classes = [c for c in self.classes] + ['disabled']
        else:
            self.classes = [c for c in self.classes if c != "disabled"]

        if image and image.container_format not in NOT_LAUNCHABLE_FORMATS:
            return image.status in ("active",)
        return False


class LaunchImageNG(LaunchImage):
    name = "launch_image_ng"
    verbose_name = _("Launch")
    classes = ("btn-launch")
    ajax = False

    def __init__(self,
                 attrs={
                     "ng-controller": "LaunchInstanceModalCtrl"
                 },
                 **kwargs):
        kwargs['preempt'] = True
        super(LaunchImage, self).__init__(attrs, **kwargs)

    def get_link_url(self, datum):
        imageId = self.table.get_object_id(datum)
        clickValue = "openLaunchInstanceWizard({successUrl: " +\
                     "'/instances/images/', imageId: '%s'})" % (imageId)
        self.attrs['ng-click'] = clickValue
        return "javascript:void(0);"


class DeleteImage(tables.DeleteAction):
    # NOTE: The bp/add-batchactions-help-text
    # will add appropriate help text to some batch/delete actions.
    help_text = _("Deleted images are not recoverable.")

    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Delete Image",
            u"Delete Images",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Deleted Image",
            u"Deleted Images",
            count
        )

    policy_rules = (("image", "delete_image"),)

    def allowed(self, request, image=None):
        # Protected images can not be deleted.
        if image and image.protected:
            return False
        if image:
            return image.owner == request.user.tenant_id
        # Return True to allow table-level bulk delete action to appear.
        return True

    def delete(self, request, obj_id):
        api.glance.image_delete(request, obj_id)

        # operation log
        api.logger.Logger(request).create(resource_type='image', action_name='Remove Image',
                                                       resource_name='Image', config=_('Image ID: %s') % obj_id,
                                                       status='Success')




class CreateImage(tables.LinkAction):
    name = "create"
    verbose_name = _("Create Image")
    url = "horizon:instances:images:images:create"
    classes = ("ajax-modal",)
    icon = "plus"
    policy_rules = (("image", "add_image"),)

    def allowed(self, request, datum):
        account_is_frozen = check_account_is_frozen(request)
        if account_is_frozen:
            if "disabled" not in self.classes:
                self.classes = [c for c in self.classes] + ['disabled']
        else:
            self.classes = [c for c in self.classes if c != "disabled"]
        return super(CreateImage, self).allowed(request, datum)


class EditImage(tables.LinkAction):
    name = "edit"
    verbose_name = _("Edit Image")
    url = "horizon:instances:images:images:update"
    classes = ("ajax-modal",)
    icon = "pencil"
    policy_rules = (("image", "modify_image"),)

    def allowed(self, request, image=None):
        if image:
            return image.status in ("active",) and \
                image.owner == request.user.tenant_id
        # We don't have bulk editing, so if there isn't an image that's
        # authorized, don't allow the action.
        return False


class CreateVolumeFromImage(tables.LinkAction):
    name = "create_volume_from_image"
    verbose_name = _("Create Volume")
    url = "horizon:storage:volumes:volumes:create"
    classes = ("ajax-modal",)
    icon = "camera"
    policy_rules = (("volume", "volume:create"),)

    def get_link_url(self, datum):
        base_url = reverse(self.url)
        params = urlencode({"image_id": self.table.get_object_id(datum)})
        return "?".join([base_url, params])

    def allowed(self, request, image=None):
        if (image and image.container_format not in NOT_LAUNCHABLE_FORMATS
                and base.is_service_enabled(request, 'volume')):
            return image.status == "active"
        return False


def filter_tenants():
    return getattr(settings, 'IMAGES_LIST_FILTER_TENANTS', [])


@memoized
def filter_tenant_ids():
    return map(lambda ft: ft['tenant'], filter_tenants())


class OwnerFilter(tables.FixedFilterAction):
    def get_fixed_buttons(self):
        def make_dict(text, tenant, icon):
            return dict(text=text, value=tenant, icon=icon)

        buttons = [make_dict(_('Custom Image'), 'user', 'fa-user')]
        for button_dict in filter_tenants():
            new_dict = button_dict.copy()
            new_dict['value'] = new_dict['tenant']
            buttons.append(new_dict)
        buttons.append(make_dict(_('Public Image'), 'public', 'fa-group'))
        return buttons

    def categorize(self, table, images):
        tenants = defaultdict(list)
        for im in images:
            categories = get_image_categories(im)
            for category in categories:
                tenants[category].append(im)
        return tenants


def get_image_categories(im):
    categories = []
    if im.is_public:
        categories.append('public')
    elif im.owner in filter_tenant_ids():
        categories.append(im.owner)
    elif not im.is_public:
        categories.append('user')
    return categories


def get_image_name(image):
    return getattr(image, "name", None) or image.id


def get_os_architecture(image):
    architecture = getattr(image, "properties", {}).get("architecture", '')
    os_type = getattr(image, "properties", {}).get("os_type", '')
    return os_type+' '+architecture

def get_image_type(image):
    return getattr(image, "properties", {}).get("image_type", "image")

def get_min_disk(image):
    return str(getattr(image, 'min_disk', '0')) + 'G'

def get_format(image):
    format = getattr(image, "disk_format", "")
    # The "container_format" attribute can actually be set to None,
    # which will raise an error if you call upper() on it.
    if not format:
        return format
    # Most image formats are untranslated acronyms, but raw is a word
    # and should be translated
    if format == "raw":
        return pgettext_lazy("Image format for display in table", u"Raw")
    return format.upper()


class UpdateRow(tables.Row):
    ajax = True

    def get_data(self, request, image_id):
        image = api.glance.image_get(request, image_id)
        return image

    def load_cells(self, image=None):
        super(UpdateRow, self).load_cells(image)
        # Tag the row with the image category for client-side filtering.
        image = self.datum
        image_categories = get_image_categories(image)
        for category in image_categories:
            self.classes.append('category-' + category)


class ImagesTable(tables.DataTable):
    STATUS_CHOICES = (
        ("active", True),
        ("saving", None),
        ("queued", None),
        ("pending_delete", None),
        ("killed", False),
        ("deleted", False),
    )
    STATUS_DISPLAY_CHOICES = (
        ("active", pgettext_lazy("Current status of an Image", u"Active")),
        ("saving", pgettext_lazy("Current status of an Image", u"Saving")),
        ("queued", pgettext_lazy("Current status of an Image", u"Queued")),
        ("pending_delete", pgettext_lazy("Current status of an Image",
                                         u"Pending Delete")),
        ("killed", pgettext_lazy("Current status of an Image", u"Killed")),
        ("deleted", pgettext_lazy("Current status of an Image", u"Deleted")),
    )
    TYPE_CHOICES = (
        ("image", pgettext_lazy("Type of an image", u"Image")),
        ("snapshot", pgettext_lazy("Type of an image", u"Snapshot")),
    )
    name = tables.Column(get_image_name,
                         link="horizon:instances:images:images:detail",
                         verbose_name=_("Image Name"))
    image_type = tables.Column(get_os_architecture,
                               verbose_name=_("Type And Architecture"))
    status = tables.Column("status",
                           verbose_name=_("Status"),
                           status=True,
                           status_choices=STATUS_CHOICES,
                           display_choices=STATUS_DISPLAY_CHOICES)
    # public = tables.Column("is_public",
    #                        verbose_name=_("Public"),
    #                        empty_value=False,
    #                        filters=(filters.yesno, filters.capfirst))
    passwd = tables.Column("is_allow_inject_passwd",
                           verbose_name=_("Allow Inject Passwd"),
                           empty_value=False,
                           filters=(filters.yesno, filters.capfirst))
    # protected = tables.Column("protected",
    #                           verbose_name=_("Protected"),
    #                           empty_value=False,
    #                           filters=(filters.yesno, filters.capfirst))
    # disk_format = tables.Column(get_format, verbose_name=_("Format"))
    size = tables.Column(get_min_disk, attrs=({"data-type": "size"}),
                         verbose_name=_("Min Disk"))
    created_at = tables.Column("created_at", verbose_name=_("Created At"),
                              filters=[ horizon_filters.parse_isotime])

    class Meta(object):
        name = "images"
        row_class = UpdateRow
        status_columns = ["status"]
        verbose_name = _("Images")
        table_actions = (OwnerFilter, CreateImage, DeleteImage,)
        launch_actions = ()
        if getattr(settings, 'LAUNCH_INSTANCE_LEGACY_ENABLED', True):
            launch_actions = (LaunchImage,) + launch_actions
        if getattr(settings, 'LAUNCH_INSTANCE_NG_ENABLED', False):
            launch_actions = (LaunchImageNG,) + launch_actions
        row_actions = launch_actions + (EditImage, DeleteImage,)
        pagination_param = "image_marker"
