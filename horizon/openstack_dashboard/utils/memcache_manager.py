# Copyright 2012 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
#
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
import memcache
from django.conf import settings


def con_memcache():
    memcached_servers = settings.CACHES.get("default").get("LOCATION")
    mc = memcache.Client(memcached_servers)
    return mc


def get_memcache_value(key):
    mc = con_memcache()
    image = mc.get(key)
    return image


def set_memcache_value(key, value):
    mc = con_memcache()
    mc.set(key, value)


def del_memcache_value(key):
    mc = con_memcache()
    mc.delete(key)








