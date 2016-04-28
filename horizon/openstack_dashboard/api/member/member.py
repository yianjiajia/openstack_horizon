# -*- coding:utf-8 -*-
from keystoneclient.auth.identity import v3
from keystoneclient import session
from keystoneclient.v3 import client
from neutronclient.v2_0 import client as neutronclient
from cinderclient import client as cinderclient
from novaclient import client as novaclient
from ceilometerclient.common.base import Manager
from ceilometerclient.v1.meters import Project
from openstack_dashboard.api import billing
from django.conf import settings
import traceback
import logging

class UserCenter():
    #认证信息：
    __tokenSession=None
    __keystone=None
    __UM=None
    __Distributor={}#分销商
    __request={}
    
    def __init__(self,request=None):
        self.initToken()
    '''
         1: 创建项目
         2: 创建用户
         3: 用户和区的对应关系
         4: 用户和项目的映射
         5: 新加cdnLimit
    '''
    def createUser(self, user, domain=None):
        user['cdnLimit']='1'
        user['parent_id']=settings.DEFAULT_USER_ID
        user["default_region_id"]=settings.DEFAULT_REGION_ID
        project_parent_id=settings.DEFAULT_PROJECT_ID
        
        if domain:
            host=self.checkHost(domain);
            if host:
                user['parent_id']=host['manager']
                user["default_region_id"]=host['default_region_id']
                project_parent_id=host['project']
        try:
            project_name = user['company']
            project=self.createProject(project_name, project_parent_id)
            userObj =self.__UM.create(project=project,**user)
            try:
                gift_balance = getattr(settings,"GIFT_BANLANCE",0)
                logging.error('settings set is %s',gift_balance)
            except Exception as e:
                logging.error('settings not set gift_balance')  
            data={"account":{'account_id':'','username':userObj.name,'project_id':project.id,'cash_balance':0,'gift_balance':gift_balance,'type':'normal','credit_line':0,'status':'normal','user_id':userObj.id}}
            try: 
                billingClinent=billing.BillingUser(self.__request)
                billingUser=billingClinent.create_billingUser(data)
                if billingUser:
                    self.setRegion(userObj.id,user["default_region_id"])
                    self.grantRole(userObj, project)
                    self.setQuota(project.id,user["default_region_id"])
                    return userObj
                else:
                    self.deleteUser(userObj)
                    self.deleteProject(project)
                    return None
                    #删除用户
            except Exception as e:
                    self.deleteUser(userObj)
                    self.deleteProject(project)
                    logging.error(str(e))
                    logging.error(traceback.format_exc())
                    return None
        except Exception as e:
            logging.error(str(e))
            logging.error(traceback.format_exc())
            return None

    '''
        创建项目
        返回项目对象
    '''
    def createProject(self, project_name,project_admin_id):
        PM = self.__keystone.projects
        project = {
            "description": "",
            "name": project_name,
            "parent_id": project_admin_id,
            "domain": "default"
        }
        project = PM.create(**project)
        return project
    
    '''
        用户－>项目->角色映射
    '''
    def grantRole(self,user,project):   
        RM = self.__keystone.roles
        user_role = RM.list(name=settings.OPENSTACK_KEYSTONE_DEFAULT_ROLE)[0]  
        RM.grant(role=user_role.id, user=user.id, project=project.id)
        grants = RM.list(user=user.id, project=project.id)
        return grants

    '''
        get default role_id for create user
    '''
    def get_default_role_id(self):
        RM = self.__keystone.roles
        user_role = RM.list(name=settings.OPENSTACK_KEYSTONE_DEFAULT_ROLE)[0]
        return user_role.id

    '''   
        设置用户<-->区域映射
    '''
    def setRegion(self,userId,regionId):
        RegionManager =self.__keystone.regions          
        region=RegionManager.add_region_to_user(user_id=userId, user_regions=[regionId])
        return region


    def setQuota(self,project_id,region):
        #neutron insert
        neutron = neutronclient.Client(session=self.__tokenSession)
        neutron.httpclient.region_name = region
        ret = neutron.update_quota(project_id, body={'quota': settings.QUOTA_DEFAULI['neutron']})
        
        #cinder
        cinder = cinderclient.Client(2, session=self.__tokenSession)#cinder insert
        CQM = cinder.quotas
        cinder_quota=settings.QUOTA_DEFAULI['cinder']
        CQM.api.client.region_name = region
        CQM.update(project_id,**cinder_quota)
        
        #nova insert
        nova = novaclient.Client(2, session=self.__tokenSession)

        QM = nova.quotas
        nova_quota=settings.QUOTA_DEFAULI['nova']
        QM.api.client.region_name = region
        QM.update(project_id,**nova_quota)
        

    '''
        授权认证
    '''    
    def initToken(self):
        auth = v3.Password(auth_url='http://'+settings.OPENSTACK_HOST+':5000/v3',
                       username=settings.ADMINUSER['name'],
                       password=settings.ADMINUSER['password'],
                       project_name='admin',
                       user_domain_id='default',
                       project_domain_name='default',
                       )
    #     auth = Token(endpoint='http://192.168.56.56:5000/v3',
    #              token='e92fad0b2b3a5e0b8155')
        self.__tokenSession = session.Session(auth=auth)
        self.__keystone= client.Client(session=self.__tokenSession)
        self.__UM = self.__keystone.users

    '''
     查找板块
     param 字典类型   
       ["name"]="###"
       ["email"]="###"
       ["telephone"] ="###" 
    '''
    def checkUser(self,param):
        if param:
            user =self.__UM.list(**param)
        else:
            user=None 
        return user    
            
    '''
        查找项目
        返回项目对象列表
    '''
    def checkProject(self,project_admin_name):
        PM = self.__keystone.projects
        search_project = PM.list(name=project_admin_name)   
        return  search_project   
          
    def get_by(self,args):
        user = self.__UM.get(args)
        if len(user) > 0:
            return user
        else:
            return 0    
    
    def getById(self,userId):
        return self.__UM.get(userId)
    '''
        更新板块
        参数： user    字符串／对象
        参数   param   字典
    '''
    def updateUser(self,user,param):
        return self.__UM.update(user,**param)
 
    '''
        删除板块
        1:删除用户
        2:删除项目
    '''
    def deleteUser(self,user):
        self.__UM.delete(user)
        
    def deleteProject(self,project):
        PM = self.__keystone.projects
        search_project = PM.delete(project)  
        
        
    # 验证域名信息    
    def checkHost(self, host):
        host_list=host.split(':')
        host=host_list[0]
        currentHost=''
        hostmanage=settings.HOSTMANAGE
        if hostmanage.has_key(host):
            currentHost=hostmanage[host]
        return currentHost

    
