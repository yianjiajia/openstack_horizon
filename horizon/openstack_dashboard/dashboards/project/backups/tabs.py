# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from django.utils.datastructures import SortedDict
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import tabs

from openstack_dashboard.api import cinder
from openstack_dashboard import api
from openstack_dashboard.dashboards.project.backups \
    import tables as backups_tables

class BackupOverviewTab(tabs.Tab):
    name = _("Overview")
    slug = "overview"
    template_name = ("storage/volumes/backups/"
                     "_detail_overview.html")

    def get_context_data(self, request):
        try:
            backup = self.tab_group.kwargs['backup']
            try:
                volume = cinder.volume_get(request, backup.volume_id)
            except Exception:
                volume = None
            return {'backup': backup,
                    'volume': volume}
        except Exception:
            redirect = reverse('horizon:storage:volumes:index')
            exceptions.handle(self.request,
                              _('Unable to retrieve backup details.'),
                              redirect=redirect)


class BackupDetailTabs(tabs.TabGroup):
    slug = "backup_details"
    tabs = (BackupOverviewTab,)


class VolumeTableMixIn(object):
    def _get_volumes(self, search_opts=None):
        try:
            return api.cinder.volume_list(self.request,
                                          search_opts=search_opts)
        except Exception:
            exceptions.handle(self.request,
                              _('Unable to retrieve volume list.'))
            return []

    def _get_instances(self, search_opts=None):
        try:
            instances, has_more = api.nova.server_list(self.request,
                                                       search_opts=search_opts)
            return instances
        except Exception:
            exceptions.handle(self.request,
                              _("Unable to retrieve volume/instance "
                                "attachment information"))
            return []

    def _get_volumes_ids_with_snapshots(self, search_opts=None):
        try:
            volume_ids = []
            snapshots = api.cinder.volume_snapshot_list(
                self.request, search_opts=search_opts)
            if snapshots:
                # extract out the volume ids
                volume_ids = set([(s.volume_id) for s in snapshots])
        except Exception:
            exceptions.handle(self.request,
                              _("Unable to retrieve snapshot list."))

        return volume_ids

    # set attachment string and if volume has snapshots
    def _set_volume_attributes(self,
                               volumes,
                               instances,
                               volume_ids_with_snapshots):
        instances = SortedDict([(inst.id, inst) for inst in instances])
        for volume in volumes:
            if volume_ids_with_snapshots:
                if volume.id in volume_ids_with_snapshots:
                    setattr(volume, 'has_snapshot', True)
            for att in volume.attachments:
                server_id = att.get('server_id', None)
                att['instance'] = instances.get(server_id, None)


class BackupsTab(tabs.TableTab, VolumeTableMixIn):
    table_classes = (backups_tables.BackupsTable,)
    name = _("Volume Backups")
    slug = "backups_tab"
    template_name = ("horizon/common/_detail_table.html")
    preload = False

    def allowed(self, request):
        return api.cinder.volume_backup_supported(self.request)

    def get_volume_backups_data(self):
        try:
            backups = api.cinder.volume_backup_list(self.request)
            volumes = api.cinder.volume_list(self.request)
            volumes = dict((v.id, v) for v in volumes)
            for backup in backups:
                backup.volume = volumes.get(backup.volume_id)
        except Exception:
            backups = []
            exceptions.handle(self.request, _("Unable to retrieve "
                                              "volume backups."))
        return backups


class BackupTableTabs(tabs.TabGroup):
    slug = "backups_tabs"
    tabs = (BackupsTab,)
    sticky = True

