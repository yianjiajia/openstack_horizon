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

from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import tabs

from openstack_dashboard import api

from openstack_dashboard.api import cinder
from openstack_dashboard.dashboards.storage.snapshots \
    import tables as vol_snapshot_tables

class OverviewTab(tabs.Tab):
    name = _("Overview")
    slug = "overview"
    template_name = ("storage/volumes/snapshots/_detail_overview.html")

    def get_context_data(self, request):
        try:
            snapshot = self.tab_group.kwargs['snapshot']
            volume = cinder.volume_get(request, snapshot.volume_id)
        except Exception:
            redirect = self.get_redirect_url()
            exceptions.handle(self.request,
                              _('Unable to retrieve snapshot details.'),
                              redirect=redirect)
        return {"snapshot": snapshot,
                "volume": volume}

    def get_redirect_url(self):
        return reverse('horizon:storage:volumes:index')


class SnapshotDetailTabs(tabs.TabGroup):
    slug = "snapshot_details"
    tabs = (OverviewTab,)

class SnapshotTab(tabs.TableTab):
    table_classes = (vol_snapshot_tables.VolumeSnapshotsTable,)
    name = _("Volume Snapshots")
    slug = "snapshots_tab"
    template_name = ("horizon/common/_detail_table.html")
    preload = False

    def get_volume_snapshots_data(self):
        if api.base.is_service_enabled(self.request, 'volume'):
            try:
                snapshots = api.cinder.volume_snapshot_list(self.request)
                volumes = api.cinder.volume_list(self.request)
                volumes = dict((v.id, v) for v in volumes)
            except Exception:
                snapshots = []
                volumes = {}
                exceptions.handle(self.request, _("Unable to retrieve "
                                                  "volume snapshots."))

            for snapshot in snapshots:
                volume = volumes.get(snapshot.volume_id)
                setattr(snapshot, '_volume', volume)
                for vol in volumes:
                    if snapshot.id==volumes.get(vol).snapshot_id:
                        setattr(snapshot, '_has_child', True)
                        break
        else:
            snapshots = []
        return snapshots

class StrategyTab(tabs.TableTab):
    table_classes = (vol_snapshot_tables.SnapshotStrategiesTable,)
    name = _("Snapshot Strategies")
    slug = "strategies_tab"
    template_name = ("horizon/common/_detail_table.html")
    preload = False

    def get_snapshot_strategies_data(self):
        try:
            strategies = api.cinder.volume_snapshot_strategy_list(self.request)
            volumes = api.cinder.volume_list(self.request)
            volumes = dict((v.id, v) for v in volumes)
        except Exception:
            strategies = []
            volumes = {}
            exceptions.handle(self.request, _("Unable to retrieve "
                                                  "volume snapshot strategies."))

        for strategy in strategies:
            volume = volumes.get(strategy.volume_id)
            setattr(strategy, '_volume', volume)

        return strategies

class SnapshotAndStrategyTabs(tabs.TabGroup):
    slug = 'snapshot_strategy_tabs'
    tabs = (SnapshotTab, StrategyTab)
    sticky = True
