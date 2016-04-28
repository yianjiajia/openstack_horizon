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

"""
Views for managing Images and Snapshots.
"""
from operator import attrgetter

from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import tables

from openstack_dashboard import api

from openstack_dashboard.dashboards.instances.images.images \
    import tables as images_tables


class IndexView(tables.DataTableView):
    table_class = images_tables.ImagesTable
    template_name = 'instances/images/index.html'
    page_title = _("Images")

    def has_prev_data(self, table):
        return self._prev

    def has_more_data(self, table):
        return self._more

    def get_data(self):
        self._prev = False
        self._more = False
        marker = self.request.GET.get(
            images_tables.ImagesTable._meta.pagination_param, None)
        prev_marker = self.request.GET.get(
            images_tables.ImagesTable._meta.prev_pagination_param, None)
        if prev_marker is not None:
            sort_dir = 'asc'
            marker = prev_marker
        else:
            sort_dir = 'desc'
        try:
            (images, self._more, self._prev) = api.glance.image_list_detailed(
                self.request, marker=marker, paginate=True, sort_dir=sort_dir)
            if prev_marker is not None:
                images = sorted(images, key=attrgetter('created_at'), reverse=True)
        except Exception:
            images = []
            exceptions.handle(self.request, _("Unable to retrieve images."))
        return images
