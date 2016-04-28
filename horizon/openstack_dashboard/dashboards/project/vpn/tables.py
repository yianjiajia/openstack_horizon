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

from django.core.urlresolvers import reverse
from django.utils.translation import pgettext_lazy
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext_lazy

from horizon import tables


forbid_updates = set(["PENDING_CREATE", "PENDING_UPDATE", "PENDING_DELETE"])


class AddSSLVPNCredentialLink(tables.LinkAction):
    name = "addsslvpncredential"
    verbose_name = _("Add SSL VPN Credential")
    url = "horizon:project:vpn:addsslvpncredential"
    classes = ("ajax-modal", "btn-addsslvpncredential",)

class DownloadOvpnFileLink(tables.LinkAction):
    name = "download_ovpnfile"
    verbose_name = _("Download OVPN File")
    classes = ("btn-download",)

    def allowed(self, request, datum=None):
            return True;

    def get_link_url(self, sslvpnconnection):
        return reverse("horizon:project:vpn:donwload_ovpn",
                       kwargs={'sslvpnconnection_id': sslvpnconnection.id})
    
class AddSSLVPNConnectionLink(tables.LinkAction):
    name = "addsslvpnconnection"
    verbose_name = _("Add SSL VPN Connection")
    url = "horizon:project:vpn:addsslvpnconnection"
    classes = ("ajax-modal", "btn-addsslvpnconnection",)


class DeleteSSLVPNCredentialLink(tables.DeleteAction):
    name="deletevpncredential" 
    action_present = _("Delete")
    action_past = _("Scheduled deletion of %(data_type)s")
    data_type_singular = _("SSL VPN Credential")
    data_type_plural = _("SSL VPN Credential")

    def allowed(self, request, datum=None):
        if datum and datum.sslvpnconns:
            return False
        return True

class DeleteSSLVPNConnectionLink(tables.DeleteAction):
    name = "deletesslvpnconnection"
    action_present = _("Delete")
    action_past = _("Scheduled deletion of %(data_type)s")
    data_type_singular = _("SSL VPN Connection")
    data_type_plural = _("SSL VPN Connections")


class UpdateSSLVPNCredentialLink(tables.LinkAction):
    name = "updatesslvpncredential"
    verbose_name = _("Edit VPN Credential")
    classes = ("ajax-modal", "btn-update",)

    def get_link_url(self, vpncredential):
        return reverse("horizon:project:vpn:update_vpncredential",
                       kwargs={'vpncredential_id': vpncredential.id})

    def allowed(self, request, datum=None):
        return True
#         return not datum['sslvpnconns']

class UpdateSSLVPNConnectionLink(tables.LinkAction):
    name = "updatesslvpnconnection"
    verbose_name = _("Edit Connection")
    classes = ("ajax-modal", "btn-update",)

    def get_link_url(self, sslvpnconnection):
        return reverse("horizon:project:vpn:update_sslvpnconnection",
            kwargs={'sslvpnconnection_id': sslvpnconnection.id})

    def allowed(self, request, datum=None):
        if datum and datum.status not in forbid_updates:
            return True
        return False
    

class SSLVPNConnectionsTable(tables.DataTable):
    STATUS_CHOICES = (
        ("Active", True),
        ("Down", True),
        ("Error", False),
    )
    STATUS_DISPLAY_CHOICES = (
        ("Active", pgettext_lazy("Current status of an ssl vpn Connection",
                                 u"Active")),
        ("Down", pgettext_lazy("Current status of an ssl vpn Connection",
                               u"Down")),
        ("Error", pgettext_lazy("Current status of an ssl vpn Connection",
                                u"Error")),
    )
    id = tables.Column('id', hidden=True)
    name = tables.Column('name', verbose_name=_('Name'),
                         link="horizon:project:vpn:sslvpnconnectiondetails")
    credential_name = tables.Column('credential_name',
                                   verbose_name=_('SSL VPN Credential'))
    vpnservice_name = tables.Column('vpnservice_name',
                                    verbose_name=_('VPN Service'))
    status = tables.Column("status",
                           verbose_name=_("Status"),
                           status=True,
                           status_choices=STATUS_CHOICES,
                           display_choices=STATUS_DISPLAY_CHOICES)
    class Meta:
        name = "sslvpnconnectionstable"
        verbose_name = _("SSL VPN Connections")
        table_actions = (AddSSLVPNConnectionLink,)
        row_actions = (DownloadOvpnFileLink, UpdateSSLVPNConnectionLink,
                       DeleteSSLVPNConnectionLink)

class AddIKEPolicyLink(tables.LinkAction):
    name = "addikepolicy"
    verbose_name = _("Add IKE Policy")
    url = "horizon:project:vpn:addikepolicy"
    classes = ("ajax-modal",)
    icon = "plus"
    policy_rules = (("network", "create_ikepolicy"),)


class AddIPSecPolicyLink(tables.LinkAction):
    name = "addipsecpolicy"
    verbose_name = _("Add IPSec Policy")
    url = "horizon:project:vpn:addipsecpolicy"
    classes = ("ajax-modal",)
    icon = "plus"
    policy_rules = (("network", "create_ipsecpolicy"),)


class AddVPNServiceLink(tables.LinkAction):
    name = "addvpnservice"
    verbose_name = _("Add VPN Service")
    url = "horizon:project:vpn:addvpnservice"
    classes = ("ajax-modal",)
    icon = "plus"
    policy_rules = (("network", "create_vpnservice"),)


class AddIPSecSiteConnectionLink(tables.LinkAction):
    name = "addipsecsiteconnection"
    verbose_name = _("Add IPSec Site Connection")
    url = "horizon:project:vpn:addipsecsiteconnection"
    classes = ("ajax-modal",)
    icon = "plus"
    policy_rules = (("network", "create_ipsec_site_connection"),)


class DeleteVPNServiceLink(tables.DeleteAction):
    name = "deletevpnservice"
    policy_rules = (("network", "delete_vpnservice"),)

    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Delete VPN Service",
            u"Delete VPN Services",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Scheduled deletion of VPN Service",
            u"Scheduled deletion of VPN Services",
            count
        )

    def allowed(self, request, datum=None):
        if datum and (datum.ipsecsiteconns or datum.sslvpnconns):
            return False
        return True


class DeleteIKEPolicyLink(tables.DeleteAction):
    name = "deleteikepolicy"
    policy_rules = (("network", "delete_ikepolicy"),)

    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Delete IKE Policy",
            u"Delete IKE Policies",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Scheduled deletion of IKE Policy",
            u"Scheduled deletion of IKE Policies",
            count
        )

    def allowed(self, request, datum=None):
        if datum and datum.ipsecsiteconns:
            return False
        return True


class DeleteIPSecPolicyLink(tables.DeleteAction):
    name = "deleteipsecpolicy"
    policy_rules = (("network", "delete_ipsecpolicy"),)

    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Delete IPSec Policy",
            u"Delete IPSec Policies",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Scheduled deletion of IPSec Policy",
            u"Scheduled deletion of IPSec Policies",
            count
        )

    def allowed(self, request, datum=None):
        if datum and datum.ipsecsiteconns:
            return False
        return True


class DeleteIPSecSiteConnectionLink(tables.DeleteAction):
    name = "deleteipsecsiteconnection"
    policy_rules = (("network", "delete_ipsec_site_connection"),)

    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Delete IPSec Site Connection",
            u"Delete IPSec Site Connections",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Scheduled deletion of IPSec Site Connection",
            u"Scheduled deletion of IPSec Site Connections",
            count
        )


class UpdateVPNServiceLink(tables.LinkAction):
    name = "update_vpnservice"
    verbose_name = _("Edit VPN Service")
    classes = ("ajax-modal", "btn-update",)
    policy_rules = (("network", "update_vpnservice"),)

    def get_link_url(self, vpnservice):
        return reverse("horizon:project:vpn:update_vpnservice",
                       kwargs={'vpnservice_id': vpnservice.id})

    def allowed(self, request, datum=None):
        if datum and datum.status not in forbid_updates:
            return True
        return False


class UpdateIKEPolicyLink(tables.LinkAction):
    name = "updateikepolicy"
    verbose_name = _("Edit IKE Policy")
    classes = ("ajax-modal", "btn-update",)
    policy_rules = (("network", "update_ikepolicy"),)

    def get_link_url(self, ikepolicy):
        return reverse("horizon:project:vpn:update_ikepolicy",
                       kwargs={'ikepolicy_id': ikepolicy.id})

    def allowed(self, request, datum=None):
        return not datum['ipsecsiteconns']


class UpdateIPSecPolicyLink(tables.LinkAction):
    name = "updateipsecpolicy"
    verbose_name = _("Edit IPSec Policy")
    classes = ("ajax-modal", "btn-update",)
    policy_rules = (("network", "update_ipsecpolicy"),)

    def get_link_url(self, ipsecpolicy):
        return reverse("horizon:project:vpn:update_ipsecpolicy",
                       kwargs={'ipsecpolicy_id': ipsecpolicy.id})

    def allowed(self, request, datum=None):
        return not datum['ipsecsiteconns']


class UpdateIPSecSiteConnectionLink(tables.LinkAction):
    name = "updateipsecsiteconnection"
    verbose_name = _("Edit Connection")
    classes = ("ajax-modal", "btn-update",)
    policy_rules = (("network", "update_ipsec_site_connection"),)

    def get_link_url(self, ipsecsiteconnection):
        return reverse("horizon:project:vpn:update_ipsecsiteconnection",
                       kwargs={'ipsecsiteconnection_id':
                               ipsecsiteconnection.id})

    def allowed(self, request, datum=None):
        if datum and datum.status not in forbid_updates:
            return True
        return False


class IPSecSiteConnectionsTable(tables.DataTable):
    STATUS_CHOICES = (
        ("Active", True),
        ("Down", True),
        ("Error", False),
    )
    STATUS_DISPLAY_CHOICES = (
        ("Active", pgettext_lazy("Current status of an IPSec Site Connection",
                                 u"Active")),
        ("Down", pgettext_lazy("Current status of an IPSec Site Connection",
                               u"Down")),
        ("Error", pgettext_lazy("Current status of an IPSec Site Connection",
                                u"Error")),
    )
    id = tables.Column('id', hidden=True)
    name = tables.Column('name_or_id', verbose_name=_('Name'),
                         link="horizon:project:vpn:ipsecsiteconnectiondetails")
    vpnservice_name = tables.Column('vpnservice_name',
                                    verbose_name=_('VPN Service'))
    ikepolicy_name = tables.Column('ikepolicy_name',
                                   verbose_name=_('IKE Policy'))
    ipsecpolicy_name = tables.Column('ipsecpolicy_name',
                                     verbose_name=_('IPSec Policy'))
    status = tables.Column("status",
                           verbose_name=_("Status"),
                           status=True,
                           status_choices=STATUS_CHOICES,
                           display_choices=STATUS_DISPLAY_CHOICES)

    class Meta(object):
        name = "ipsecsiteconnectionstable"
        verbose_name = _("IPSec Site Connections")
        table_actions = (AddIPSecSiteConnectionLink,
                         DeleteIPSecSiteConnectionLink)
        row_actions = (UpdateIPSecSiteConnectionLink,
                       DeleteIPSecSiteConnectionLink)

class SSLVPNCredentialsTable(tables.DataTable):
    id = tables.Column('id', hidden=True)
    name = tables.Column("name", verbose_name=_('Name'),
                         link="horizon:project:vpn:sslvpncredentialdetails")
    description = tables.Column('description', verbose_name=_('Description'))

    class Meta:
        name = "sslvpncredentialstable"
        verbose_name = _("SSL VPN Credential")
        table_actions = (AddSSLVPNCredentialLink,)
        row_actions = (UpdateSSLVPNCredentialLink, DeleteSSLVPNCredentialLink)

class VPNServicesTable(tables.DataTable):
    STATUS_CHOICES = (
        ("Active", True),
        ("Down", True),
        ("Error", False),
    )
    STATUS_DISPLAY_CHOICES = (
        ("Active", pgettext_lazy("Current status of a VPN Service",
                                 u"Active")),
        ("Down", pgettext_lazy("Current status of a VPN Service",
                               u"Down")),
        ("Error", pgettext_lazy("Current status of a VPN Service",
                                u"Error")),
        ("Created", pgettext_lazy("Current status of a VPN Service",
                                  u"Created")),
        ("Pending_Create", pgettext_lazy("Current status of a VPN Service",
                                         u"Pending Create")),
        ("Pending_Update", pgettext_lazy("Current status of a VPN Service",
                                         u"Pending Update")),
        ("Pending_Delete", pgettext_lazy("Current status of a VPN Service",
                                         u"Pending Delete")),
        ("Inactive", pgettext_lazy("Current status of a VPN Service",
                                   u"Inactive")),
    )
    id = tables.Column('id', hidden=True)
    name = tables.Column("name_or_id", verbose_name=_('Name'),
                         link="horizon:project:vpn:vpnservicedetails")
    description = tables.Column('description', verbose_name=_('Description'))
    subnet_name = tables.Column('subnet_name', verbose_name=_('Subnet'))
    router_name = tables.Column('router_name', verbose_name=_('Router'))
    status = tables.Column("status",
                           verbose_name=_("Status"),
                           status=True,
                           status_choices=STATUS_CHOICES,
                           display_choices=STATUS_DISPLAY_CHOICES)

    class Meta(object):
        name = "vpnservicestable"
        verbose_name = _("VPN Services")
        table_actions = (AddVPNServiceLink,)
        row_actions = (UpdateVPNServiceLink, DeleteVPNServiceLink)


class IKEPoliciesTable(tables.DataTable):
    id = tables.Column('id', hidden=True)
    name = tables.Column("name_or_id", verbose_name=_('Name'),
                         link="horizon:project:vpn:ikepolicydetails")
    auth_algorithm = tables.Column('auth_algorithm',
                                   verbose_name=_('Authorization algorithm'))
    encryption_algorithm = tables.Column(
        'encryption_algorithm',
        verbose_name=_('Encryption algorithm'))
    pfs = tables.Column("pfs", verbose_name=_('PFS'))

    class Meta(object):
        name = "ikepoliciestable"
        verbose_name = _("IKE Policies")
        table_actions = (AddIKEPolicyLink, DeleteIKEPolicyLink)
        row_actions = (UpdateIKEPolicyLink, DeleteIKEPolicyLink)


class IPSecPoliciesTable(tables.DataTable):
    id = tables.Column('id', hidden=True)
    name = tables.Column("name_or_id", verbose_name=_('Name'),
                         link="horizon:project:vpn:ipsecpolicydetails")
    auth_algorithm = tables.Column('auth_algorithm',
                                   verbose_name=_('Authorization algorithm'))
    encryption_algorithm = tables.Column(
        'encryption_algorithm',
        verbose_name=_('Encryption algorithm'))
    pfs = tables.Column("pfs", verbose_name=_('PFS'))

    class Meta(object):
        name = "ipsecpoliciestable"
        verbose_name = _("IPSec Policies")
        table_actions = (AddIPSecPolicyLink, DeleteIPSecPolicyLink,)
        row_actions = (UpdateIPSecPolicyLink, DeleteIPSecPolicyLink)
