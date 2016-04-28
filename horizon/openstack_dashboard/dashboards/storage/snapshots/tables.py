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

import logging
import traceback

from django.http import HttpResponse  # noqa

from django.core.urlresolvers import reverse
from django.utils import html
from django.utils.http import urlencode
from django.utils import safestring
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext_lazy

from horizon import tables
from horizon.utils.functions import check_account_is_frozen

from openstack_dashboard import api
from openstack_dashboard.api import base
from openstack_dashboard.api import cinder
from openstack_dashboard import policy

from openstack_dashboard.dashboards.storage.volumes \
    .volumes import tables as volume_tables
from openstack_dashboard.dashboards.storage.snapshots \
    .strategies.forms import _make_strategy_snapshot_at_choices

LOG = logging.getLogger(__name__)

class LaunchSnapshot(volume_tables.LaunchVolume):
    name = "launch_snapshot"

    def get_link_url(self, datum):
        base_url = reverse(self.url)

        vol_id = "%s:snap" % self.table.get_object_id(datum)
        params = urlencode({"source_type": "volume_snapshot_id",
                            "source_id": vol_id})
        return "?".join([base_url, params])

    def allowed(self, request, snapshot=None):
        if snapshot:
            if (snapshot._volume and
                    getattr(snapshot._volume, 'bootable', '') == 'true'):
                return snapshot.status == "available"
        return False


class DeleteVolumeSnapshot(policy.PolicyTargetMixin, tables.DeleteAction):
    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Delete Volume Snapshot",
            u"Delete Volume Snapshots",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Scheduled deletion of Volume Snapshot",
            u"Scheduled deletion of Volume Snapshots",
            count
        )

    def allowed(self, request, snapshot=None):
        if snapshot:
            return not getattr(snapshot,'_has_child', False)
        return True

    policy_rules = (("volume", "volume:delete_snapshot"),)
    policy_target_attrs = (("project_id",
                            'os-extended-snapshot-attributes:project_id'),)

    def delete(self, request, obj_id):
        api.cinder.volume_snapshot_delete(request, obj_id)

        # operation log
        api.logger.Logger(request).create(resource_type='snapshot', action_name='Delete Snapshot',
                                                       resource_name='Snapshot', config='Snapshot ID: '+ obj_id,
                                                       status='Success')


class FlattenVolumeSnapshot(policy.PolicyTargetMixin, tables.BatchAction):
    name = "flatten_snapshot"
    classes = ("btn-danger",)
    icon = "cloud-upload"
    policy_rules = (("volume", "volume:flatten_snapshot"),)
    policy_target_attrs = (("project_id",
                            'os-extended-snapshot-attributes:project_id'),)

    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Flatten of Snapshot",
            u"Flatten of Snapshots",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Scheduled flatten of Snapshot",
            u"Scheduled flatten of Snapshots",
            count
        )

    def allowed(self, request, snapshot=None):
        if snapshot:
            return getattr(snapshot,'_has_child', False)
        return False

    def action(self, request, obj_id):
        try:
            api.cinder.volume_snapshot_flatten(request, obj_id)
        except Exception:
            LOG.error(traceback.format_exc())
            LOG.error('Unable to flatten volume snapshot.')


class EditVolumeSnapshot(policy.PolicyTargetMixin, tables.LinkAction):
    name = "edit"
    verbose_name = _("Edit Snapshot")
    url = "horizon:storage:snapshots:update"
    classes = ("ajax-modal",)
    icon = "pencil"
    policy_rules = (("volume", "volume:update_snapshot"),)
    policy_target_attrs = (("project_id",
                            'os-extended-snapshot-attributes:project_id'),)

    def allowed(self, request, snapshot=None):
        return snapshot.status == "available"


class CreateVolumeFromSnapshot(tables.LinkAction):
    name = "create_from_snapshot"
    verbose_name = _("Create Volume")
    url = "horizon:storage:volumes:volumes:create"
    classes = ("ajax-modal",)
    icon = "camera"
    policy_rules = (("volume", "volume:create"),)

    def get_link_url(self, datum):
        base_url = reverse(self.url)
        params = urlencode({"snapshot_id": self.table.get_object_id(datum)})
        return "?".join([base_url, params])

    def allowed(self, request, volume=None):
        if volume and base.is_service_enabled(request, 'volume'):
            return volume.status == "available"
        return False


class UpdateRow(tables.Row):
    ajax = True

    def get_data(self, request, snapshot_id):
        snapshot = cinder.volume_snapshot_get(request, snapshot_id)
        snapshot._volume = cinder.volume_get(request, snapshot.volume_id)
        return snapshot


class SnapshotVolumeNameColumn(tables.Column):
    def get_raw_data(self, snapshot):
        volume = snapshot._volume
        if volume:
            volume_name = volume.name
            volume_name = html.escape(volume_name)
        else:
            volume_name = _("Unknown")
        return safestring.mark_safe(volume_name)

    def get_link_url(self, snapshot):
        volume = snapshot._volume
        if volume:
            volume_id = volume.id
            return reverse(self.link, args=(volume_id,))


class VolumeSnapshotsFilterAction(tables.FilterAction):

    def filter(self, table, snapshots, filter_string):
        """Naive case-insensitive search."""
        query = filter_string.lower()
        return [snapshot for snapshot in snapshots
                if query in snapshot.name.lower()]


class VolumeSnapshotsTable(volume_tables.VolumesTableBase):
    name = tables.Column("name",
                         verbose_name=_("Name"),
                         link="horizon:storage:volumes:snapshots:detail")
    volume_name = SnapshotVolumeNameColumn(
        "name",
        verbose_name=_("Volume Name"),
        link="horizon:storage:volumes:volumes:detail")

    class Meta(object):
        name = "volume_snapshots"
        verbose_name = _("Volume Snapshots")
        table_actions = (VolumeSnapshotsFilterAction, DeleteVolumeSnapshot,)
        row_actions = (LaunchSnapshot,
                       EditVolumeSnapshot, DeleteVolumeSnapshot, FlattenVolumeSnapshot)
        row_class = UpdateRow
        status_columns = ("status",)
        permissions = ['openstack.services.volume']


class CreateSnapshotStrategy(tables.LinkAction):
    name = "create"
    verbose_name = _("Create Strategy")
    url = "horizon:storage:snapshots:strategies:create_strategy"
    classes = ("ajax-modal", "btn-create")
    icon = "plus"
    policy_rules = (("volume", "volume:create"),)
    ajax = True

    def __init__(self, attrs=None, **kwargs):
        kwargs['preempt'] = True
        super(CreateSnapshotStrategy, self).__init__(attrs, **kwargs)

    def allowed(self, request, volume=None):
        account_is_frozen = check_account_is_frozen(request)
        if account_is_frozen:
            if "disabled" not in self.classes:
                self.classes = [c for c in self.classes] + ['disabled']
        else:
            self.classes = [c for c in self.classes if c != "disabled"]
        return True

    def single(self, table, request, object_id=None):
        self.allowed(request, None)
        return HttpResponse(self.render())

class SnapshotStrategiesFilterAction(tables.FilterAction):

    def filter(self, table, strategies, filter_string):
        """Naive case-insensitive search."""
        query = filter_string.lower()
        return [snapshot for snapshot in strategies
                if query in snapshot.name.lower()]

class EditSnapshotStrategy(policy.PolicyTargetMixin, tables.LinkAction):
    name = "edit"
    verbose_name = _("Edit Snapshot Strategy")
    url = "horizon:storage:snapshots:strategies:update"
    classes = ("ajax-modal",)
    icon = "pencil"
    policy_rules = (("volume", "volume:update_snapshot_strategy"),)
    policy_target_attrs = (("project_id",
                            'os-extended-snapshot-attributes:project_id'),)

    def allowed(self, request, strategy=None):
        account_is_frozen = check_account_is_frozen(request)
        if account_is_frozen:
            if "disabled" not in self.classes:
                self.classes = [c for c in self.classes] + ['disabled']
        else:
            self.classes = [c for c in self.classes if c != "disabled"]
        return True

class DeleteSnapshotStrategy(policy.PolicyTargetMixin, tables.DeleteAction):
    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            _(u"Delete Strategy"),
            _(u"Delete Strategies"),
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Scheduled deletion of Snapshot Strategy",
            u"Scheduled deletion of Snapshot Strategies",
            count
        )

    def allowed(self, request, strategy=None):
        #if strategy:
        #    return not getattr(strategy,'_has_child', False)
        return True

    policy_rules = (("volume", "volume:delete_snapshot_strategy"),)
    policy_target_attrs = (("project_id",
                            'os-extended-snapshot-attributes:project_id'),)

    def delete(self, request, obj_id):
        api.cinder.volume_snapshot_strategy_delete(request, obj_id)

        # operation log
        api.logger.Logger(request).create(resource_type='strategy', action_name='Delete Strategy',
                                                       resource_name='Strategy', config='Strategy ID: '+ obj_id,
                                                       status='Success')

class UpdateStrategyRow(tables.Row):
    ajax = True

    def get_data(self, request, strategy_id):
        strategy = cinder.volume_snapshot_get(request, strategy_id)
        strategy._volume = cinder.volume_get(request, strategy_id.volume_id)
        return strategy

class StrategyVolumeNameColumn(tables.Column):
    def get_raw_data(self, strategy):
        volume = strategy._volume
        if volume:
            volume_name = volume.name
            volume_name = html.escape(volume_name)
        else:
            volume_name = _("Unknown")
        return safestring.mark_safe(volume_name)

    def get_link_url(self, strategy):
        volume = strategy._volume
        if volume:
            volume_id = volume.id
            return reverse(self.link, args=(volume_id,))

class SnapshotAtColumn(tables.Column):

    def get_raw_data(self, strategy):
        snapshot_at = strategy.snapshot_at
        if snapshot_at:
            choices = dict(_make_strategy_snapshot_at_choices())
            snapshot_at = choices.get(str(snapshot_at), _("Unknown"))
        else:
            snapshot_at = _("Unknown")
        return safestring.mark_safe(snapshot_at)

class StatusColumn(tables.Column):
    def get_raw_data(self, strategy):
        return _("OK") if strategy.status else _("Not")

class KeepLastSundayColumn(tables.Column):
    def get_raw_data(self, strategy):
        return _("OK") if strategy.keep_last_sunday else _("Not")

class SnapshotStrategiesTable(tables.DataTable):
    name = tables.Column("name",
                         verbose_name=_("Name"),
                         link="horizon:storage:snapshots:strategies:detail")
    volume_name = StrategyVolumeNameColumn("name",
                                           verbose_name=_("Volume Name"),
                                           link="horizon:storage:volumes:volumes:detail")
    status = StatusColumn("status", verbose_name=_("Use or Not"))
    snapshot_at = SnapshotAtColumn("snapshot_at", verbose_name=_("Snapshot At"))
    keep_last_sunday = KeepLastSundayColumn("keep_last_sunday", verbose_name=_("Keep Last Sunday or Not"))
    max_keep_number = tables.Column("max_keep_number", verbose_name=_("Max Keep Snapshot Numbers"))

    class Meta(object):
        name = "snapshot_strategies"
        verbose_name = _("Snapshot Strategies")
        table_actions = (SnapshotStrategiesFilterAction, CreateSnapshotStrategy, DeleteSnapshotStrategy)
        row_actions = (EditSnapshotStrategy, DeleteSnapshotStrategy,)
        row_class = UpdateStrategyRow
        permission = ['openstack.services.volume']
