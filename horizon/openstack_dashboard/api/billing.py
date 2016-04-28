# -*- coding:utf-8 -*-
'''
Created on 2014-7-7

@author: baoguodong.kevin
'''
import urllib2
import urllib
from django.conf import settings
from django.utils.translation import gettext as _
import json
from horizon import exceptions
import uuid
import logging
import traceback
from openstack_dashboard.utils import Pagination
import datetime
import pytz
LOG = logging.getLogger(__name__)


class RequestClient(object):
    def __init__(self, request=None, base_url=None):
        self.base_url = base_url if base_url else settings.BILLING_BASE_URL
        self.request = request

    def api_request(self, url, method='GET', headers={}, data=None, isJson=True):
        if isJson:
            headers['Content-Type'] = 'application/json'
        else:
            data = urllib.urlencode(data)
        req = urllib2.Request(self.base_url+url, headers=headers)
        if method in ['PUT', 'DELETE']:
            req.get_method = lambda: method
        response = urllib2.urlopen(req, data)
        return response

    def get_account(self, project_id=None):
        account = None
        url = '/account/getaccountbyprojectid/'+str(project_id or self.request.user.tenant_id)
        ret = json.loads(self.api_request(url).read())
        if ret['success'] == 'success' and ret['account']:
            account = ret['account']
        return account
    
def request(url,method='GET', headers={}, data=None, isJson=True):
    requestClient=RequestClient()
    return json.loads(requestClient.api_request(url, method, headers, data, isJson).read())

def getAdvertList():
    url='/advert/getvalidadvert'
    return request(url)

def getParentUserById(user_id):
    url='/account/getparentuserbyid/'+user_id
    return request(url)

class BillingItem(RequestClient):
    rest_url = '/billingItem/list'
    def billing_item(self):
        bill_dict = {}
        ratio_item_id = {}
        try:
            discount = Discount(self.request).get_discount()
            if discount:
                for i in discount:
                    ratio_item_id[i['billing_item_id']] = i['discount_ratio']
            region = self.request.user.services_region
            url = self.rest_url+'?region_id='+str(region)
            ret = json.loads(self.api_request(url).read())
            if ret['success'] == 'success':
                bill = ret['billing_itemList']
                if bill:
                    for j in bill:
                        if j['billing_item_id'] in ratio_item_id.keys():
                            bill_dict[str(j['billing_item'])] = float('%0.4f' % (float(j['price'])*float(ratio_item_id[j['billing_item_id']])))
                        else:
                            bill_dict[str(j['billing_item'])] = float(j['price'])
        except Exception:
            exceptions.handle(self.request)
        return bill_dict




class Discount(RequestClient):
    rest_url = '/discount/list/'

    def get_discount(self):
        discount = []
        account = self.get_account()
        # region = self.request.user.services_region
        if account:
            url = self.rest_url+account['account_id']
            ret = json.loads(self.api_request(url).read())
            if ret['success'] == 'success':
                discount = ret['discountList']
        return discount




    
#创建billing 用户    
class BillingUser(RequestClient):
    #前台注册/后台管理员--创建用户
    def create_billingUser(self,data):
        try:
            url = '/account/create'
            if 'account_id' in data['account']:
                data['account']['account_id']=self.getUUID()
            ret = json.loads(self.api_request(url,method='POST',data=json.dumps(data)).read())
            if ret['success'] == 'success':
                return True
            else:
                return False
        except Exception as e:
            LOG.error(str(e))
            LOG.error(traceback.format_exc())
            return False  
        

    def getUUID(self):
        return uuid.uuid4().__str__()

#获取billing中的workorder工单信息
class BillingWorkOrder(RequestClient):
    def get_url(self,url,params):
        params={key:value for key,value in params.items() if value!=None}
        return url+"?"+urllib.urlencode(params)
    def create_workorder(self,params={}):
        '''
        创建新工单
        :return:
        '''
        url="/workorder/create/workorder"
        response=json.loads(self.api_request(url,method='POST',data=json.dumps(params)).read())
        if response['success']=="success":
            return True
        else:
            return False
    def create_record(self,params={}):
        '''
        创建工单记录
        :return:
        '''
        url="/workorder/create/record"
        response=json.loads(self.api_request(url,method='POST',data=json.dumps(params)).read())
        if response['success']=="success":
            return True
        else:
            return False

    def get_wordorder_list(self,params={}):
        '''
        获取工单列表
        :return:
        '''
        url=self.get_url("/workorder/list/workorder",params)
        url_status=self.get_url("/workorder/statics",{"apply_by":params["apply_by"]})
        page_no=int(params.get("pageNo"))
        page_size=int(params.get("pageSize"))
        info=json.loads(self.api_request(url_status).read())
        response=json.loads(self.api_request(url).read())
        if response['success']=="success" and info["success"]=="success":
            data=response["workorders"]
            total=response["total"]
            pagenation=Pagination.PageResult(total, page_no, page_size).get_pagination()
            return [self.workorderobj(self.to2obj(item)) for item in data],pagenation,info["statics"]
        else:
            return False

    def get_record_list(self,params={}):
        '''
        获取工单记录列表
        :return:
        '''
        url=self.get_url("/workorder/list/record",params)
        response=json.loads(self.api_request(url).read())
        if response['success']=="success":
            return response
        else:
            return False
    def get_type_list(self,params={}):
        '''
        获取工单类型信息
        :return:
        '''
        url=self.get_url("/workorder/list/type",params)
        response=json.loads(self.api_request(url).read())
        if response['success']=="success":
            return response
        else:
            return False
    def get_workorder_detail(self,params):
        '''
        获取工单的详细信息
        :param params:
        :return:
        '''
        workorderno=params.pop("workorderno") if params.get("workorderno") else None
        if workorderno:
            url=self.get_url("/workorder/detail/"+workorderno,params)
        else:
            return False
        response=json.loads(self.api_request(url).read())
        if response['success']=="success":
            data=response["detail"]
            if data["status"]=="confirmed":
                data["isconfirmed"]=True
            else:
                data["isconfirmed"]=False
            data["status"]=_("work order "+data["status"]) if data["status"] else None
            data["apply_at"]=datetime.datetime.strptime(data["apply_at"],"%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.UTC).astimezone(pytz.timezone('Asia/Shanghai')).strftime("%Y-%m-%d %H:%M:%S") if data["apply_at"] else None
            data["created_at"]=datetime.datetime.strptime(data["created_at"],"%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.UTC).astimezone(pytz.timezone('Asia/Shanghai')).strftime("%Y-%m-%d %H:%M:%S") if data["created_at"] else None
            data["lasthandled_at"]=datetime.datetime.strptime(data["lasthandled_at"],"%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.UTC).astimezone(pytz.timezone('Asia/Shanghai')).strftime("%Y-%m-%d %H:%M:%S") if data["lasthandled_at"] else None
            data["updated_at"]=datetime.datetime.strptime(data["updated_at"],"%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.UTC).astimezone(pytz.timezone('Asia/Shanghai')).strftime("%Y-%m-%d %H:%M:%S") if data["updated_at"] else None
            records=data.pop("records")
            for record in records:
                record["status"]=_("work order "+record["status"]) if record["status"] else None
                record["created_at"]=datetime.datetime.strptime(record["created_at"],"%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.UTC).astimezone(pytz.timezone('Asia/Shanghai')).strftime("%Y-%m-%d %H:%M:%S") if record["created_at"] else None
                record["record_at"]=datetime.datetime.strptime(record["record_at"],"%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.UTC).astimezone(pytz.timezone('Asia/Shanghai')).strftime("%Y-%m-%d %H:%M:%S") if record["record_at"] else None
                record["updated_at"]=datetime.datetime.strptime(record["updated_at"],"%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.UTC).astimezone(pytz.timezone('Asia/Shanghai')).strftime("%Y-%m-%d %H:%M:%S") if record["updated_at"] else None
            data["records"]=records
            return data
        else:
            return False

    def to2obj(self,dict):
        current=WorkOrder()
        for key in dict:
            setattr(current,key,dict[key])
        return current

    def workorderobj(self,obj):
        '''
        对WorkOrder对象添加操作字段
        '''
        workorder_detail_view = "horizon:settings:workorder:detail"
        from django.core.urlresolvers import reverse

        workorderno=getattr(obj,"workorder_no")
        details_url=reverse(workorder_detail_view,kwargs={"workorderno":workorderno})
        from django.utils.safestring import mark_safe
        if getattr(obj,"status")=="confirmed":
            trans_string=_("Work Order Closed")
            operate=mark_safe("<a href='"+details_url+"'>"+trans_string+"</a>")
        else:
            trans_string=_("Work Order Operate")
            operate=mark_safe("<a href='"+details_url+"'>"+trans_string+"</a>")
        setattr(obj,"operate",operate)
        obj.apply_at=datetime.datetime.strptime(obj.apply_at,"%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.UTC).astimezone(pytz.timezone('Asia/Shanghai')).strftime("%Y-%m-%d %H:%M:%S") if obj.apply_at else None
        obj.created_at=datetime.datetime.strptime(obj.created_at,"%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.UTC).astimezone(pytz.timezone('Asia/Shanghai')).strftime("%Y-%m-%d %H:%M:%S") if obj.created_at else None
        obj.lasthandled_at=datetime.datetime.strptime(obj.lasthandled_at,"%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.UTC).astimezone(pytz.timezone('Asia/Shanghai')).strftime("%Y-%m-%d %H:%M:%S") if obj.lasthandled_at else None
        obj.updated_at=datetime.datetime.strptime(obj.updated_at,"%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.UTC).astimezone(pytz.timezone('Asia/Shanghai')).strftime("%Y-%m-%d %H:%M:%S") if obj.updated_at else None
        if obj.status=="confirmed":
            setattr(obj,"isconfirmed",True)
        else:
            setattr(obj,"isconfirmed",False)
        obj.status=_("work order "+obj.status) if obj.status else None
        return obj

class WorkOrder(object):
    '''


    '''
