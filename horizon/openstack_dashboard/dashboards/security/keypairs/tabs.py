# Copyright 2012 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
#
# Copyright 2012 Nebula, Inc.
# Copyright 2012 OpenStack Foundation
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

from horizon import exceptions
from horizon import tabs

from openstack_dashboard.api import nova

from openstack_dashboard.dashboards.security.\
    keypairs.tables import KeypairsTable



class KeypairsTab(tabs.TableTab):
    table_classes = (KeypairsTable,)
    name = _("Key Pairs")
    slug = "keypairs_tab"
    template_name = "horizon/common/_detail_table.html"
    permissions = ('openstack.services.compute',)

    def get_keypairs_data(self):
        try:
            keypairs = nova.keypair_list(self.request)
        except Exception:
            keypairs = []
            exceptions.handle(self.request,
                              _('Unable to retrieve key pair list.'))
        return keypairs


class KeypariTabs(tabs.TabGroup):
    slug = "keypair_tabs"
    tabs = (KeypairsTab,)
    sticky = True
