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

from collections import defaultdict
import itertools
import logging

from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon.utils.memoized import memoized  # noqa

from openstack_dashboard.api import base
from openstack_dashboard.api import cinder
from openstack_dashboard.api import network
from openstack_dashboard.api import neutron
from openstack_dashboard.api import nova
from openstack_dashboard.api import lbaas


LOG = logging.getLogger(__name__)

NOVA_QUOTA_FIELDS = ("metadata_items",
                     "cores",
                     "instances",
                     "injected_files",
                     "injected_file_content_bytes",
                     "ram",
                     "floating_ips",
                     "fixed_ips",
                     "security_groups",
                     "security_group_rules",)

MISSING_QUOTA_FIELDS = ("key_pairs",
                        "injected_file_path_bytes",)

CINDER_QUOTA_FIELDS = ("volumes",
                       "snapshots",
                       "volume_gigabytes",
                       "snapshot_gigabytes",)

NEUTRON_QUOTA_FIELDS = ("network",
                        "subnet",
                        "port",
                        "router",
                        "floatingip",
                        "security_group",
                        "security_group_rule",
                        "bandwidth",
                        "pool"
                        )

QUOTA_FIELDS = NOVA_QUOTA_FIELDS + CINDER_QUOTA_FIELDS + NEUTRON_QUOTA_FIELDS

QUOTA_NAMES = {
    "metadata_items": _('Metadata Items'),
    "cores": _('VCPUs'),
    "instances": _('Instances'),
    "injected_files": _('Injected Files'),
    "injected_file_content_bytes": _('Injected File Content Bytes'),
    "ram": _('RAM (MB)'),
    "floating_ips": _('Floating IPs'),
    "fixed_ips": _('Fixed IPs'),
    "security_groups": _('Security Groups'),
    "security_group_rules": _('Security Group Rules'),
    "key_pairs": _('Key Pairs'),
    "injected_file_path_bytes": _('Injected File Path Bytes'),
    "volumes": _('Volumes'),
    "snapshots": _('Volume Snapshots'),
    "gigabytes": _('Total Size of Volumes and Snapshots (GB)'),
    "network": _("Networks"),
    "subnet": _("Subnets"),
    "port": _("Ports"),
    "router": _("Routers"),
    "floatingip": _('Floating IPs'),
    "security_group": _("Security Groups"),
    "security_group_rule": _("Security Group Rules")
}


class QuotaUsage(dict):
    """Tracks quota limit, used, and available for a given set of quotas."""

    def __init__(self):
        self.usages = defaultdict(dict)

    def __contains__(self, key):
        return key in self.usages

    def __getitem__(self, key):
        return self.usages[key]

    def __setitem__(self, key, value):
        raise NotImplementedError("Directly setting QuotaUsage values is not "
                                  "supported. Please use the add_quota and "
                                  "tally methods.")

    def __repr__(self):
        return repr(dict(self.usages))

    def get(self, key, default=None):
        return self.usages.get(key, default)

    def add_quota(self, quota):
        """Adds an internal tracking reference for the given quota."""
        if quota.limit is None or quota.limit == -1:
            # Handle "unlimited" quotas.
            self.usages[quota.name]['quota'] = float("inf")
            self.usages[quota.name]['available'] = float("inf")
        else:
            if isinstance(quota.limit, int):
                self.usages[quota.name]['quota'] = int(quota.limit)
            else:
                self.usages[quota.name]['quota'] = quota.limit

    def tally(self, name, value):
        """Adds to the "used" metric for the given quota."""
        value = value or 0  # Protection against None.
        # Start at 0 if this is the first value.
        if 'used' not in self.usages[name]:
            self.usages[name]['used'] = 0
        # Increment our usage and update the "available" metric.
        self.usages[name]['used'] += int(value)  # Fail if can't coerce to int.
        self.update_available(name)

    def update_available(self, name):
        """Updates the "available" metric for the given quota."""
        available = self.usages[name]['quota'] - self.usages[name]['used']
        if available < 0:
            available = 0
        self.usages[name]['available'] = available


def _get_quota_data(request, method_name, disabled_quotas=None,
                    tenant_id=None, region=None):
    quotasets = []
    if not tenant_id:
        tenant_id = request.user.tenant_id
    quotasets.append(getattr(nova, method_name)(request, tenant_id, region))
    qs = base.QuotaSet()
    if disabled_quotas is None:
        disabled_quotas = get_disabled_quotas(request)
    if 'volumes' not in disabled_quotas:
        quotasets.append(getattr(cinder, method_name)(request, tenant_id, region))
    for quota in itertools.chain(*quotasets):
        if quota.name not in disabled_quotas:
            qs[quota.name] = quota.limit
    return qs


def get_default_quota_data(request, disabled_quotas=None, tenant_id=None):
    return _get_quota_data(request,
                           "default_quota_get",
                           disabled_quotas=disabled_quotas,
                           tenant_id=tenant_id)


def get_tenant_quota_data(request, disabled_quotas=None, tenant_id=None, region=None):
    qs = _get_quota_data(request,
                         "tenant_quota_get",
                         disabled_quotas=disabled_quotas,
                         tenant_id=tenant_id,
                         region=region)

    # TODO(jpichon): There is no API to get the default system quotas
    # in Neutron (cf. LP#1204956), so for now handle tenant quotas here.
    # This should be handled in _get_quota_data() eventually.
    if not disabled_quotas:
        return qs

    # Check if neutron is enabled by looking for network and router
    if 'network' and 'router' not in disabled_quotas:
        tenant_id = tenant_id or request.user.tenant_id
        neutron_quotas = neutron.tenant_quota_get(request, tenant_id, region=region)
        # add pool quota(pool now is loadbalancer)
        pool_quota = neutron_quotas.get('pool').limit
        qs.add(base.QuotaSet({'pool': pool_quota}))
    if 'floating_ips' in disabled_quotas:
        # Neutron with quota extension disabled
        if 'floatingip' in disabled_quotas:
            qs.add(base.QuotaSet({'floating_ips': -1}))
        # Neutron with quota extension enabled
        else:
            # Rename floatingip to floating_ips since that's how it's
            # expected in some places (e.g. Security & Access' Floating IPs)
            fips_quota = neutron_quotas.get('floatingip').limit
            qs.add(base.QuotaSet({'floating_ips': fips_quota}))
    if 'security_groups' in disabled_quotas:
        if 'security_group' in disabled_quotas:
            qs.add(base.QuotaSet({'security_groups': -1}))
        # Neutron with quota extension enabled
        else:
            # Rename security_group to security_groups since that's how it's
            # expected in some places (e.g. Security & Access' Security Groups)
            sec_quota = neutron_quotas.get('security_group').limit
            qs.add(base.QuotaSet({'security_groups': sec_quota}))
    if 'network' in disabled_quotas:
        for item in qs.items:
            if item.name == 'networks':
                qs.items.remove(item)
                break
    else:
        net_quota = neutron_quotas.get('network').limit
        qs.add(base.QuotaSet({'networks': net_quota}))
    if 'subnet' in disabled_quotas:
        for item in qs.items:
            if item.name == 'subnets':
                qs.items.remove(item)
                break
    else:
        net_quota = neutron_quotas.get('subnet').limit
        qs.add(base.QuotaSet({'subnets': net_quota}))
    if 'router' in disabled_quotas:
        for item in qs.items:
            if item.name == 'routers':
                qs.items.remove(item)
                break
    else:
        router_quota = neutron_quotas.get('router').limit
        qs.add(base.QuotaSet({'routers': router_quota}))

    return qs


def get_disabled_quotas(request):
    disabled_quotas = []

    # Cinder
    if not base.is_service_enabled(request, 'volume'):
        disabled_quotas.extend(CINDER_QUOTA_FIELDS)

    # Neutron
    if not base.is_service_enabled(request, 'network'):
        disabled_quotas.extend(NEUTRON_QUOTA_FIELDS)
    else:
        # Remove the nova network quotas
        disabled_quotas.extend(['floating_ips', 'fixed_ips'])

        if neutron.is_extension_supported(request, 'security-group'):
            # If Neutron security group is supported, disable Nova quotas
            disabled_quotas.extend(['security_groups', 'security_group_rules'])
        else:
            # If Nova security group is used, disable Neutron quotas
            disabled_quotas.extend(['security_group', 'security_group_rule'])

        try:
            if not neutron.is_quotas_extension_supported(request):
                disabled_quotas.extend(NEUTRON_QUOTA_FIELDS)
        except Exception:
            LOG.exception("There was an error checking if the Neutron "
                          "quotas extension is enabled.")

    return disabled_quotas


def _get_tenant_compute_usages(request, usages, disabled_quotas, tenant_id, region=None):
    if tenant_id:
        instances, has_more = nova.server_list(
            request, search_opts={'tenant_id': tenant_id}, all_tenants=True, region=region)
    else:
        instances, has_more = nova.server_list(request, region=region)

    # Fetch deleted flavors if necessary.
    flavors = dict([(f.id, f) for f in nova.flavor_list(request)])
    missing_flavors = [instance.flavor['id'] for instance in instances
                       if instance.flavor['id'] not in flavors]
    for missing in missing_flavors:
        if missing not in flavors:
            try:
                flavors[missing] = nova.flavor_get(request, missing)
            except Exception:
                flavors[missing] = {}
                exceptions.handle(request, ignore=True)

    usages.tally('instances', len(instances))

    # Sum our usage based on the flavors of the instances.
    # change by zhihao.ding 2015/7/17 for kill_flavor start
    #for flavor in [flavors[instance.flavor['id']] for instance in instances]:
    #    usages.tally('cores', getattr(flavor, 'vcpus', None))
    #    usages.tally('ram', getattr(flavor, 'ram', None))
    for instance in instances:
        usages.tally('cores', instance.vcpus)
        usages.tally('ram', instance.memory_mb)
    # change by zhihao.ding 2015/7/17 for kill_flavor end

    # Initialise the tally if no instances have been launched yet
    if len(instances) == 0:
        usages.tally('cores', 0)
        usages.tally('ram', 0)


def _get_tenant_network_usages(request, usages, disabled_quotas, tenant_id, region=None):
    floating_ips = []
    try:
        if network.floating_ip_supported(request):
            floating_ips = network.floating_ip_list(request, region=region, tenant_id=tenant_id)
            if tenant_id:
                floating_ips = filter(lambda fip: fip.tenant_id == tenant_id, floating_ips)
    except Exception:
        raise
        pass
    usages.tally('floating_ips', len(floating_ips))

    if 'security_group' not in disabled_quotas:
        security_groups = []
        security_groups = network.security_group_list(request)
        usages.tally('security_groups', len(security_groups))

    if 'network' not in disabled_quotas:
        networks = []
        networks = neutron.network_list(request, shared=False, region=region)
        if tenant_id:
            networks = filter(lambda net: net.tenant_id == tenant_id, networks)
        usages.tally('networks', len(networks))

    if 'subnet' not in disabled_quotas:
        subnets = []
        subnets = neutron.subnet_list(request, region=region)
        if tenant_id:
            subnets = filter(lambda subnet: subnet.tenant_id == tenant_id, subnets)
        usages.tally('subnets', len(subnets))

    if 'router' not in disabled_quotas:
        routers = []
        routers = neutron.router_list(request, region=region)
        if tenant_id:
            routers = filter(lambda rou: rou.tenant_id == tenant_id, routers)
        usages.tally('routers', len(routers))
    if 'pool' not in disabled_quotas:
        pools = []
        pools = lbaas.pool_list(request)
        if tenant_id:
            pools = filter(lambda p: p.tenant_id == tenant_id, pools)
        usages.tally('pool', len(pools))



def _get_tenant_volume_usages(request, usages, disabled_quotas, tenant_id, region=None):
    if 'volumes' not in disabled_quotas:
        if tenant_id:
            opts = {'all_tenants': 1}
            volumes = cinder.volume_list(request, opts, region=region)
            snapshots = cinder.volume_snapshot_list(request, opts, region=region)
            volumes = filter(lambda v: v.to_dict()['os-vol-tenant-attr:tenant_id'] == tenant_id, volumes)
            snapshots = filter(lambda s: s.to_dict()['os-extended-snapshot-attributes:project_id'] == tenant_id, snapshots)
        else:
            volumes = cinder.volume_list(request)
            snapshots = cinder.volume_snapshot_list(request)
        # all_size = sum([int(v.size) for v in volumes]) + sum([int(s.size) for s in snapshots])
        volume_size = sum([int(v.size) for v in volumes])
        snapshot_size = sum([int(s.size) for s in snapshots])
        usages.tally('volume_gigabytes', volume_size)
        usages.tally('snapshot_gigabytes', snapshot_size)
        usages.tally('volumes', len(volumes))
        usages.tally('snapshots', len(snapshots))


@memoized
def tenant_quota_usages(request, tenant_id=None, region=None):
    """Get our quotas and construct our usage object.
    If no tenant_id is provided, a the request.user.project_id
    is assumed to be used
    """
    if not tenant_id:
        tenant_id = request.user.project_id

    disabled_quotas = get_disabled_quotas(request)
    usages = QuotaUsage()

    for quota in get_tenant_quota_data(request,
                                       disabled_quotas=disabled_quotas,
                                       tenant_id=tenant_id,
                                       region=region):
        usages.add_quota(quota)

    # Get our usages.
    _get_tenant_compute_usages(request, usages, disabled_quotas, tenant_id, region)
    _get_tenant_network_usages(request, usages, disabled_quotas, tenant_id, region)
    _get_tenant_volume_usages(request, usages, disabled_quotas, tenant_id, region)

    return usages


def tenant_limit_usages(request):
    # TODO(licostan): This method shall be removed from Quota module.
    # ProjectUsage/BaseUsage maybe used instead on volume/image dashboards.
    limits = {}

    try:
        limits.update(nova.tenant_absolute_limits(request))
    except Exception:
        msg = _("Unable to retrieve compute limit information.")
        exceptions.handle(request, msg)

    if base.is_service_enabled(request, 'volume'):
        try:
            limits.update(cinder.tenant_absolute_limits(request))
            volumes = cinder.volume_list(request)
            snapshots = cinder.volume_snapshot_list(request)
            total_size = sum([getattr(volume, 'size', 0) for volume
                              in volumes])
            limits['gigabytesUsed'] = total_size
            limits['volumesUsed'] = len(volumes)
            limits['snapshotsUsed'] = len(snapshots)
        except Exception:
            msg = _("Unable to retrieve volume limit information.")
            exceptions.handle(request, msg)

    return limits
