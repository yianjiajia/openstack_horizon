#!/bin/bash
CURR_PATH=`pwd`
cd $CURR_PATH/../
python manager.py collectstatic
python manager.py compress
\cp openstack_dashboard/local/local_settings.py.example /etc/openstack-dashboard/local_settions.py
ln -s /etc/openstack-dashboard/local_settions.py /etc/openstack-dashboard/local_settions
sedj -i "s/WEB_ROOT = '/dashboard'/WEB_ROOT = ''/" /etc/openstack-dashboard/local_settions
