
# -*- coding:utf-8 -*-
'''
Created on 2015-10-30

@author: gaga.yan

'''
import urllib2
import urllib
from django.conf import settings
import json
import logging
from django.utils.translation import ugettext_lazy as _
from openstack_dashboard.utils import Pagination
import traceback

LOG = logging.getLogger(__name__)
logging.basicConfig(level = logging.DEBUG)

class RequestClient(object):
    def __init__(self, request, base_url=None):
        self.base_url = base_url if base_url else settings.LOG_BASE_URL
        self.request = request

    def api_request(self, url, method='GET', headers={}, data=None, isJson=True):
        if isJson:
            headers['Content-Type'] = 'application/json'
        else:
            data = urllib.urlencode(data)
        req = urllib2.Request(self.base_url+url, headers=headers)
        if method in ['PUT', 'DELETE', 'POST']:
            req.get_method = lambda: method
        response = urllib2.urlopen(req, json.dumps(data))
        return response

    def get_project_id(self):
        return self.request.user.project_id

    def get_user_id(self):
        return self.request.user.id

    def get_project_name(self):
        return self.request.user.project_name

    def get_user_name(self):
        return self.request.user.username

    def get_region(self):
        return self.request.user.services_region


class Logger(RequestClient):
    rest_url = {'log_list':'/logger/list', 'log_create':'/logger/create'}
    # 日志语句规则
    LOG_FORMAT = {
            'action_log':
        {
            'project_id': None,
            'user_id': None,
            'project_name':None,
            'user_name':None,
            'resource_type': None,
            'action_name': None,
            'resource_name': None,
            'region': None,
            'config': None,
            'status': None

        }
        }
    # 创建日志接口封装
    def create(self, resource_type=None, action_name=None, resource_name=None, config=None, status=None):
        self.LOG_FORMAT['action_log']['project_id'] = self.get_project_id()
        self.LOG_FORMAT['action_log']['user_id'] = self.get_user_id()
        self.LOG_FORMAT['action_log']['project_name'] = self.get_project_name()
        self.LOG_FORMAT['action_log']['user_name'] = self.get_user_name()
        self.LOG_FORMAT['action_log']['region'] = self.get_region()
        self.LOG_FORMAT['action_log']['resource_type'] = resource_type
        self.LOG_FORMAT['action_log']['action_name'] = action_name
        self.LOG_FORMAT['action_log']['resource_name'] = resource_name
        self.LOG_FORMAT['action_log']['config'] = config
        self.LOG_FORMAT['action_log']['status'] = status
        url = self.rest_url['log_create']
        try:
            self.api_request(url, method='POST',data=self.LOG_FORMAT)
        except Exception as e:
            LOG.error(str(e))
            LOG.error(traceback.format_exc())
            return True
    # 查询日志接口封装
    def query(self,url):
        logger_data = {}
        data = []
        try:
            ret = self.api_request(url)
            clean_data = json.loads(ret.read())
            if clean_data['success'] == 'success':
                total = clean_data['logList']['total']
                page_no = clean_data['logList']['page_no']
                page_size = clean_data['logList']['page_size']
                pagination = Pagination.PageResult(total, page_no, page_size).get_pagination()
                for i in clean_data['logList']['logs']:
                    data.append(Log(**i))
                logger_data['data'] = data
                logger_data['pagination'] = pagination
                return logger_data
            return {}
        except Exception as e:
            LOG.error(str(e))
            LOG.error(traceback.format_exc())
            return {}

    def list(self, **kwargs):
        role_name = self.request.user.roles[0].get('name')
        if self.request.user.is_superuser or role_name == 'support':
            url = self.rest_url['log_list']
            query = '?'+'&'.join(['%s=%s'%(key, value) for (key, value) in kwargs.items()
                                  if value != 'all' and value !=None and value != ''])
            query = '' if query == '?' else query
            url = url + query
            return self.query(url)
        else:
            project_id = self.get_project_id()
            user_id = self.get_user_id()
            url = self.rest_url['log_list']+'?project_id='+project_id+'&user_id='+user_id
            query = '&'.join(['%s=%s'%(key, value) for (key, value) in kwargs.items()
                              if value != 'all' and value !=None])
            query = query if query else ''
            connect = '&' if query else ''
            url = url + connect + query
            return self.query(url)

class Log(object):
    '''log 对象封装'''
    def __init__(self, **kwargs):
        """

        :rtype : object
        """
        self.id = kwargs.get('id',None)
        self.project_id = kwargs.get('project_id', None)
        self.user_id = kwargs.get('user_id', None)
        self.project_name = kwargs.get('project_name', None)
        self.user_name = kwargs.get('user_name', None)
        self.resource_type = _(kwargs.get('resource_type',None))
        self.action_name = _(kwargs.get('action_name', None))
        self.resource_name = _(kwargs.get('resource_name', None))
        self.region = _(kwargs.get('region',None))
        self.config = _(kwargs.get('config',None))
        self.action_at = kwargs.get('action_at', None)
        self.status = _(kwargs.get('status', None))


