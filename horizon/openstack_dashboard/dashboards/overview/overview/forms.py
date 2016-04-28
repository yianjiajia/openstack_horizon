import logging
import uuid
import random
import traceback
import time

from django.utils.translation import ugettext_lazy as _
from django.core.validators import MaxValueValidator
from django.forms import ValidationError  # noqa
from django.conf import settings
from django.core.urlresolvers import reverse

from horizon import forms
from horizon import exceptions
from horizon import messages

from openstack_dashboard.exceptions import NOT_FOUND
from openstack_dashboard import api
from openstack_dashboard.utils import vpncredential

LOG = logging.getLogger(__name__)


class InitNetForm(forms.SelfHandlingForm):
    bandwidth = forms.IntegerField(label=_('Bandwidth (Mbps)'),
                                  min_value=1)

    def __init__(self, request, *args, **kwargs):
        super(InitNetForm, self).__init__(request, *args, **kwargs)
        if not request.user.is_superuser:
            max_router_bandwidth_for_user = getattr(settings, 'MAX_ROUTER_BANDWIDTH_FOR_USER', 50)
            self.fields['bandwidth'].validators.append(MaxValueValidator(max_router_bandwidth_for_user))

    def handle(self, request, data):
        # net
        try:
            params = {'name': 'network',
                      'admin_state_up': True}
            network = api.neutron.network_create(request, **params)

        except Exception as e:
            msg = (_('Failed to create network %(reason)s') %
                   {"reason": e})
            LOG.info(msg)

            # operation log
            api.logger.Logger(request).create(resource_type='network', action_name='Create Network',
                                                       resource_name='Network', config='',
                                                       status='Error')
            return False

        # subnet
        params = {}
        current_region = request.session['services_region']
        try:
            params = {'name': 'subnet',
                      'network_id': network.id,
                      'cidr': settings.NET_INIT_CONFIG[current_region]['cidr'],
                      'ip_version': 4,
                      'dns_nameservers': settings.NET_INIT_CONFIG[current_region]['dns_servers'],
                      'enable_dhcp': True}
            params['tenant_id'] = request.user.tenant_id
            subnet = api.neutron.subnet_create(request, **params)

            # operation log
            config = _('Subnet Name: %s') % 'subnet'

            api.logger.Logger(request).create(resource_type='network', action_name='Create Subnet',
                                                       resource_name='Network', config=config,
                                                       status='Success')
        except Exception as e:
            msg = (_('Failed to create subnet %(reason)s') %
                   {"reason": e})
            LOG.info(msg)

            # operation log
            api.logger.Logger(request).create(resource_type='network', action_name='Create Subnet',
                                                       resource_name='Network', config=msg,
                                                       status='Error')
            return False
        # router
        params = {}
        try:
            params = {'admin_state_up': True,
                      'name': 'router'}
            params['tenant_id'] = request.user.tenant_id

            search_opts = {'router:external': True}
            networks = api.neutron.network_list(request, **search_opts)
            if len(networks) > 0:  # TODO
                params['external_gateway_info'] = {'network_id': networks[0].id}

            params['bandwidth'] = data['bandwidth']
            router = api.neutron.router_create(request, **params)

            # operation log
            config = _('Route Name: %s Bandwidth: %s') %('route', data['bandwidth'])
            api.logger.Logger(request).create(resource_type='network', action_name='Create Route',
                                                       resource_name='Network', config=config,
                                                       status='Success')
        except Exception as e:
            msg = (_('Failed to create router %(reason)s') %
                   {"reason": e})
            LOG.info(msg)

            # operation log
            api.logger.Logger(request).create(resource_type='network', action_name='Create Route',
                                                       resource_name='Network', config=msg,
                                                       status='Error')
            return False

        # connect router and subnet
        try:
            api.neutron.router_add_interface(request, router.id, subnet_id=subnet.id)

        except Exception as e:
            msg = (_('Failed to create router %(reason)s') %
                   {"reason": e})
            LOG.info(msg)

            # operation log
            api.logger.Logger(request).create(resource_type='network', action_name='Create Network',
                                                       resource_name='Network', config=msg,
                                                       status='Error')
            return False

        msg = _('Network was successfully created.')
        messages.success(request, msg)

        # operation log
        config = _('Network Name: %s') %'network'

        api.logger.Logger(request).create(resource_type='network', action_name='Create Network',
                                                       resource_name='Network', config=config,
                                                       status='Success')
        return True


class InitVPNForm(forms.SelfHandlingForm):
    name = forms.CharField(label=_('Name'),
                           initial="DefaultVPN",
                           widget=forms.TextInput(
                               attrs={'readonly': 'readonly'}))

    def handle(self, request, context):
        # credential
        try:
            temp_dir = "/tmp/vpncredentials/" + uuid.uuid4().get_hex() + "/"
            result = vpncredential.createCredential(temp_dir)
            context['description'] = ''
            if result:
                context["ca"] = vpncredential.readFileContent(temp_dir + "ca.crt")
                context["server_certificate"] = vpncredential.readFileContent(temp_dir + "server.crt")
                context["server_key"] = vpncredential.readFileContent(temp_dir + "server.key")
                context["dh"] = vpncredential.readFileContent(temp_dir + "dh1024.pem")
                context["client_certificate"] = vpncredential.readFileContent(temp_dir + "client.crt")
                context["client_key"] = vpncredential.readFileContent(temp_dir + "client.key")
                result = api.vpn.vpncredential_create(request, **context)
                vpncredential.cleanCredential(temp_dir)
        except Exception as e:
            msg = (_('Unable to create VPN credential. %(reason)s') %
                   {"reason": e})
            LOG.info(msg)

            # operation log
            api.logger.Logger(request).create(resource_type='vpn', action_name='Create VPN',
                                                       resource_name='VPN', config=msg,
                                                       status='Error')
            return False
        tenant_id = request.user.tenant_id
        # service
        try:
            networks = api.neutron.network_list_for_tenant(request, tenant_id)
        except Exception:
            msg = _('Unable to retrieve networks list.')
            LOG.info(msg)

            # operation log
            api.logger.Logger(request).create(resource_type='vpn', action_name='Create VPN',
                                                       resource_name='VPN', config=msg,
                                                       status='Error')
            return False
        if len(networks) == 0:
            msg = _('no network')
            LOG.info(msg)
            return False
        elif len(networks) > 1:
            msg = _('more than one network')
            LOG.info(msg)
            return False
        else:
            context['subnet_id'] = networks[0]['subnets'][0].id
        try:
            routers = api.neutron.router_list(request, tenant_id=tenant_id)
        except Exception:
            msg = _('Unable to retrieve routers list.')
            LOG.info(msg)

            # operation log
            api.logger.Logger(request).create(resource_type='vpn', action_name='Create VPN',
                                                       resource_name='VPN', config=msg,
                                                       status='Error')
            return False
        if len(routers) == 0:
            msg = _('no router')
            LOG.info(msg)
            return False
        elif len(routers) > 1:
            msg = _('more than one router')
            LOG.info(msg)
            return False
        else:
            context['router_id'] = routers[0].id
            context['admin_state_up'] = True
            context['description'] = ''
        try:
            vpnservice = api.vpn.vpnservice_create(request, **context)
        except Exception:
            msg = _('Unable to create vpn service.')
            LOG.info(msg)

            # operation log
            api.logger.Logger(request).create(resource_type='vpn', action_name='Create VPN',
                                                       resource_name='VPN', config=msg,
                                                       status='Error')
            return False

        # connection
        try:
            vpncredentials = api.vpn.sslvpncredential_list(request, tenant_id=tenant_id)
        except Exception:
            exceptions.handle(request,
                              _('Unable to retrieve vpn credential list.'))

            # operation log
            api.logger.Logger(request).create(resource_type='vpn', action_name='Create VPN',
                                                       resource_name='VPN', config=_('Unable to retrieve vpn credential list.'),
                                                       status='Error')
            return False
        context['credential_id'] = vpncredentials[0].id
        context['vpnservice_id'] = vpnservice.id
        context['client_address_pool_cidr'] = "192.168.80.0/24"
        context['description'] = ''
        context['admin_state_up'] = True
        try:
            api.vpn.sslvpnconnection_create(request, **context)
        except Exception:
            exceptions.handle(request, _('Unable to create ssl connection.'))

            # operation log
            api.logger.Logger(request).create(resource_type='vpn', action_name='Create VPN',
                                                       resource_name='VPN', config=_('Unable to create ssl connection.'),
                                                       status='Error')
            return False
        msg = _('VPN was successfully created.')
        messages.success(request, msg)

        # operation log
        config = _('VPN Name: %s') % 'DefaultVPN'

        api.logger.Logger(request).create(resource_type='vpn', action_name='Create VPN',
                                                       resource_name='VPN', config=config,
                                                       status='Success')
        return True


class InitFireWallForm(forms.SelfHandlingForm):
    PORTS_CHOICES = (
        ('80', '80 (HTTP)'),
        ('1194', '1194 (OpenVPN)'),
        ('icmp', 'ICMP'),
        ('22', '22 (SSH)'),
        ('53', '53 (DNS)'),
        ('3389', '3389 (Remote)'),
        ('443', '443 (HTTPS)'),
        ('23', '23 (Telnet)'),
        ('21', '21 (FTP)'),
        ('3306', '3306 (MySQL)'),
        ('1433', '1433 (SQLServer)'),
        ('1723', '1723 (PPTP)'),
        ('69', '69 (TFTP)'),
    )

    ports_list = forms.MultipleChoiceField(label=_("Ports"), required=False,
                                           widget=forms.CheckboxSelectMultiple, choices=PORTS_CHOICES,
                                           initial=['80', '1194', '53', '22', 'icmp', '3389', '443'])

    def handle(self, request, context):
        # rule
        params = {'protocol': u'', 'name': u'', 'enabled': True, 'source_ip_address': None,
                  'destination_ip_address': None, 'source_port': None, 'action': u'allow', 'destination_port': None,
                  'description': u''}

        ports_list = context['ports_list']
        for port in ports_list:
            if port == 'icmp':
                params['protocol'] = 'icmp'
                params['destination_port'] = None
            elif port in ['53', '69']:
                params['protocol'] = 'udp'
                params['destination_port'] = port
            else:
                params['protocol'] = 'tcp'
                params['destination_port'] = port
            params['name'] = port
            try:
                api.fwaas.rule_create(request, **params)
            except Exception as e:
                exceptions.handle(request, str(e))
                return False
        # policy
        params = {'name': 'default_policy'}
        try:
            policy = api.fwaas.policy_create(request, **params)
        except Exception as e:
            exceptions.handle(request, str(e))
            return False
        # add rule to policy
        policy_id = policy.id
        tenant_id = request.user.tenant_id
        try:
            all_rules = api.fwaas.rule_list_for_tenant(request, tenant_id)
        except Exception as e:
            msg = _('Failed to retrieve available rules: %s') % e
            LOG.error(msg)
            exceptions.handle(request, msg)
            return False
        for rule in all_rules:
            try:
                body = {'firewall_rule_id': rule.id,
                        'insert_before': '',
                        'insert_after': ''}
                policy = api.fwaas.policy_insert_rule(request, policy_id, **body)  # TODO, orders
            except Exception as e:
                msg = _('Failed to insert rule to policy ')
                LOG.error(msg)
                exceptions.handle(request, msg)
                return False
        # add policy to firewall, add router
        try:
            routers_list = api.fwaas.firewall_unassociated_routers_list(
                request, tenant_id)
        except Exception as e:
            routers_list = []
            exceptions.handle(request,
                              _('Unable to retrieve routers (%(error)s).') % {
                                  'error': str(e)})
            return False
        if len(routers_list) > 0:
            params = {'router_ids': [routers_list[0].id], 'description': u'', 'name':
                u'default_firewall', 'firewall_policy_id': policy_id}
        else:
            params = {'router_ids': [], 'description': u'', 'name':
                u'default_firewall', 'firewall_policy_id': policy_id}
        try:
            api.fwaas.firewall_create(request, **params)

            # operation log
            config = _('Firewall Name: %s') %'default_firewall'
            api.logger.Logger(request).create(resource_type='firewall', action_name='Create Firewall',
                                                       resource_name='Firewall', config=config,
                                                       status='Success')
        except Exception as e:
            exceptions.handle(request, str(e))

            # operation log
            api.logger.Logger(request).create(resource_type='firewall', action_name='Create Firewall',
                                                       resource_name='Firewall', config='',
                                                       status='Error')
            return False
        msg = _('Firewall was successfully created.')
        messages.success(request, msg)
        return True


class DestroyForm(forms.SelfHandlingForm):
    verify_code = forms.CharField(label=_('Verify Code'),
                           widget=forms.TextInput(
                               attrs={'readonly': 'readonly'}))
    confirm_verify_code = forms.CharField(label=_('Confirm Verify Code'))

    def __init__(self, request, *args, **kwargs):
        super(DestroyForm, self).__init__(request, *args, **kwargs)
        self.fields['verify_code'].initial = str(random.random())[2:8]

    def clean(self):
        data = super(forms.Form, self).clean()
        if data['verify_code'] != data['confirm_verify_code']:
            raise ValidationError(_('Confirm code not right.'))
        return data

    def destroy_all(self, request, context):
        redirect = reverse("horizon:overview:overview:index")
        tenant_id = self.request.user.tenant_id
        #destroy instance
        try:
            instances, self._more = api.nova.server_list(
                self.request)
        except Exception:
            exceptions.handle(self.request,
                              _('Unable to retrieve instances.'), redirect=redirect)
            return False
        for inst in instances:
            api.nova.server_delete(request, inst.id)

        #destroy loadbalancer
        try:
            lbs = api.lbaas.pool_list(request, tenant_id=tenant_id)
        except Exception:
            exceptions.handle(self.request,
                              _('Unable to retrieve loadbalancers.'), redirect=redirect)
            return False
        for lb in lbs:
            obj_id = lb.id
            try:
                pool = api.lbaas.pool_get(request, obj_id)
            except Exception as e:
                exceptions.handle(request,
                                  _('Unable to locate Loadbalancer to delete. %s')
                                  % e, redirect=redirect)
                return False
            # delete vip
            vip_id = pool.vip_id
            if vip_id is not None:
                try:
                    api.lbaas.vip_delete(request, vip_id)
                except Exception as e:
                    exceptions.handle(request,
                                      _('Unable to delete VIP. %s') % e, redirect=redirect)
                    return False
            # delete pool
            try:
                api.lbaas.pool_delete(request, obj_id)
            except Exception as e:
                exceptions.handle(request,
                                  _('Unable to delete pool. %s') % e, redirect=redirect)
                return False
            # delete monitors
            monitors = pool.health_monitors
            if monitors is not None:
                for mon in monitors:
                    try:
                        api.lbaas.pool_health_monitor_delete(request, mon.id)
                    except Exception as e:
                        exceptions.handle(request,
                                          _('Unable to delete monitor. %s') % e, redirect=redirect)
                        return False

        #destroy vpn
        try:
            conns = api.vpn.sslvpnconnection_list(request, tenant_id=tenant_id)
        except Exception:
            exceptions.handle(request,_('Unable to retrieve SSL Connection list.'), redirect=redirect)
            return False
        for con in conns:
            api.vpn.sslvpnconnection_delete(request, con.id)

        try:
            vpnservices = api.vpn.vpnservice_list(request, tenant_id=tenant_id)
        except Exception:
            exceptions.handle(request,
                              _('Unable to retrieve VPN Services list.'), redirect=redirect)
            return False
        for vp in vpnservices:
            api.vpn.vpnservice_delete(request, vp.id)

        try:
            credentials = api.vpn.sslvpncredential_list(request, tenant_id=tenant_id)
        except Exception:
            exceptions.handle(request,
                              _('Unable to retrieve VPN Credential list.'), redirect=redirect)
            return False
        for cre in credentials:
            api.vpn.vpncredential_delete(request, cre.id)

        #destroy firewall
        firewalls = api.fwaas.firewall_list_for_tenant(request, tenant_id)
        for fw in firewalls:
            api.fwaas.firewall_delete(request, fw.id)

        if firewalls:
            time.sleep(3) #TODO delay 3 second to delete
        policies = api.fwaas.policy_list_for_tenant(request, tenant_id)
        for p in policies:
            api.fwaas.policy_delete(request, p.id)

        rules = api.fwaas.rule_list_for_tenant(request, tenant_id)
        for r in rules:
            api.fwaas.rule_delete(request, r.id)

        #floating ip
        try:
            floating_ips = api.network.tenant_floating_ip_list(self.request)
            for fp in floating_ips:
                api.network.tenant_floating_ip_release(request, fp.id)
        except Exception as e:
            LOG.error(traceback.format_exc())

        #destroy virtnic
        search_opts = {"flag": "manual", "tenant_id": tenant_id}
        ports = api.neutron.port_list(self.request, **search_opts)
        for p in ports:
            api.neutron.port_delete(request, p.id)

        #destroy net
        routers = api.neutron.router_list(request, tenant_id=tenant_id)
        if routers:
            for r in routers:
                search_opts = {'device_owner': 'network:router_interface',
                               'device_id': r.id}
                ports = api.neutron.port_list(request, **search_opts)
                for port in ports:
                    api.neutron.router_remove_interface(request, r.id,
                                                        port_id=port.id)
                api.neutron.router_delete(request, r.id)

        networks = api.neutron.network_list_for_tenant(request, tenant_id)
        for n in networks:
            for subnet in n.subnets:
                api.neutron.subnet_delete(request, subnet.id)
            api.neutron.network_delete(request, n.id)

        #destroy keypair
        keypairs = api.nova.keypair_list(request)
        for k in keypairs:
            api.nova.keypair_delete(request, k.id)

        #destroy volume
        try:
            snapshots = api.cinder.volume_snapshot_list(self.request)
            volume_ids = set([s.volume_id for s in snapshots])
            volumes = api.cinder.volume_list(self.request)
        except Exception:
            snapshots = []
            volumes = {}
            exceptions.handle(self.request, _("Unable to retrieve "
                                              "volume snapshots."))
        for snapshot in snapshots:
            for vol in volumes:
                if snapshot.id == vol.snapshot_id:
                    child_list = [v.id for v in volumes if v.snapshot_id == snapshot.id]
                    setattr(snapshot, '_has_child', True)
                    setattr(snapshot, 'child_list', child_list)
                    break
        for volume in volumes:
            if volume_ids:
                if volume.id in volume_ids:
                    setattr(volume, 'has_snapshot', True)
                    snapshot_list = [s.id for s in snapshots if s.volume_id == volume.id]
                    setattr(volume, 'snapshot_list', snapshot_list)

        def destory_snapshot(request, snapshot):
            if getattr(snapshot, '_has_child', False):
                for child in snapshot.child_list:
                    vol = [v for v in volumes if v.id == child][0]
                    try:
                        destory_volume(request, vol)
                    except NOT_FOUND:
                        pass
                    except Exception as e:
                        print 'error' + e
                api.cinder.volume_snapshot_delete(request, snapshot.id)
                for volume in volumes:
                    if getattr(volume, 'has_snapshot', False):
                        if snapshot.id in volume.snapshot_list:
                            index = volume.snapshot_list.index(snapshot.id)
                            volume.snapshot_list.pop(index)
                            if len(volume.snapshot_list) == 0:
                                setattr(volume,'_has_child', False)
            else:
                api.cinder.volume_snapshot_delete(request, snapshot.id)
            time.sleep(3)

        def destory_volume(request, volume):
            if getattr(volume,'has_snapshot', False):
                for snap in volume.snapshot_list:
                    snapshot = [s for s in snapshots if s.id == snap][0]
                    try:
                        destory_snapshot(request, snapshot)
                    except NOT_FOUND:
                        pass
                    except Exception:
                        print 'error'
                api.cinder.volume_delete(request, volume.id)
                for snapshot in snapshots:
                    if getattr(snapshot, '_has_child', False):
                        if volume.id in snapshot.child_list:
                            index = snapshot.child_list.index(volume.id)
                            snapshot.child_list.pop(index)
                            if len(snapshot.child_list) == 0:
                                setattr(snapshot,'_has_child', False)
            else:
                api.cinder.volume_delete(request, volume.id)
            time.sleep(3)

        for vol in volumes:
            destory_volume(request, vol)

        # destroy image
        try:
            (images, _more, _prev) = api.glance.image_list_detailed(self.request)
        except Exception:
            images = []
            exceptions.handle(self.request, _("Unable to retrieve images."))
        for img in images:
            if not img.is_public:
                api.glance.image_delete(request, img.id)

        messages.success(request, _('Successfully delete resources'))
        return True

    def handle(self, request, context):
        try:
            ret = self.destroy_all(request, context)
            api.logger.Logger(request).create(resource_type='destroy_all_resources', action_name='Destroy all resources',
                                              resource_name='Destroy all resources', config='',
                                              status='Success')
            return ret
        except Exception:
            api.logger.Logger(request).create(resource_type='destroy_all_resources', action_name='Destroy all resources',
                                              resource_name='Destroy all resources', config='',
                                              status='Error')
            exceptions.handle(request, 'destroy resource failed')
            return False
