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

from django.utils.translation import ugettext_lazy as _

import horizon

'''
class BasePanels(horizon.PanelGroup):
    slug = "compute"
    name = _("Compute")
    panels = ('overview',
              'instances',
              'volumes',
              'images',
              'access_and_security',)


class NetworkPanels(horizon.PanelGroup):
    slug = "network"
    name = _("Network")
    panels = ('network_topology',
              'networks',
              'routers',
              'loadbalancers',
              'firewalls',
              'vpn',)


class ObjectStorePanels(horizon.PanelGroup):
    slug = "object_store"
    name = _("Object Store")
    panels = ('containers',)


class OrchestrationPanels(horizon.PanelGroup):
    slug = "orchestration"
    name = _("Orchestration")
    panels = ('stacks',
              'stacks.resource_types',)


class DatabasePanels(horizon.PanelGroup):
    slug = "database"
    name = _("Database")
    panels = ('databases',
              'database_backups',)


class DataProcessingPanels(horizon.PanelGroup):
    slug = "data_processing"
    name = _("Data Processing")
    panels = ('data_processing.wizard',
              'data_processing.clusters',
              'data_processing.job_executions',
              'data_processing.cluster_templates',
              'data_processing.nodegroup_templates',
              'data_processing.jobs',
              'data_processing.job_binaries',
              'data_processing.data_sources',
              'data_processing.data_image_registry',
              'data_processing.data_plugins',)


class Project(horizon.Dashboard):
    name = _("Project")
    slug = "project"
    panels = (
        BasePanels,
        NetworkPanels,
        #ObjectStorePanels,
        OrchestrationPanels,
        DatabasePanels,
        DataProcessingPanels,
        )
    default_panel = 'overview'
'''


class Overview(horizon.Dashboard):
    name = _("Overview")
    slug = "project"
    default_panel = 'overview'
    panels = ('overview',
              'network_topology')

# class Compute(horizon.Dashboard):
#     name = _("Compute")
#     slug = "compute"
#     default_panel = 'instances'
#     panels = ('instances',
#               'images',)

# class Storage(horizon.Dashboard):
#     name = _("Storage")
#     slug = "storage"
#     default_panel = "volumes"
#     panels = ('volumes',
#               'backups',)

class Network(horizon.Dashboard):
    name = _("Network")
    slug = "network"
    default_panel = "networks"
    panels = ('network_topology',
              'networks',
              'floating_ips',
              'routers',
              'virtnic',
              'loadbalancers',
              'vpn',)

class Cdn(horizon.Dashboard):
    name = _("CDN")
    slug = "cdn"
    default_panel = "cdn.cdn_domain_manager"
    panels = ('cdn.cdn_domain_manager',
              'cdn.cdn_cache_refresh',
              'cdn.cdn_monitor_report',
              'cdn.cdn_log_manager',)

class Security(horizon.Dashboard):
    name = _("Security")
    slug = "security"
    default_panel = "firewalls"
    panels = ('firewalls',
              'access_and_security',)


# horizon.register(Overview)
# horizon.register(Compute)
# horizon.register(Overview)
# horizon.register(Storage)
# horizon.register(Network)
# horizon.register(Security)
# horizon.register(Cdn)
