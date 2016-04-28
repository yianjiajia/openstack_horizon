# -*- coding:utf-8 -*-
from openstack_dashboard.api.member.member import *
import re
import time
from django.conf import settings
'''
args 字典
验证用户输入数据
'''
def checkuser(args):
    userC = UserCenter() 
    param={}
    user_obj={}
    if "inputUsername" in args:
        #用户名查找用户  
        param["name"]=args["inputUsername"]
    if "inputEmail" in args:
        #邮箱查找用户
        param["email"]=args["inputEmail"] 
    if "mobile" in args:
        #邮箱查找用户
        param["telephone"]=args["mobile"]  
    if "compName" in args:
        #邮箱查找用户
        param["company"]=args["compName"]  
    if param:            
        user_obj  =userC.checkUser(param)    
    return user_obj

'''
args 字典
验证项目名是否存在
'''
def checkproject(args):
    userC = UserCenter() 
    projec_obj={}
    if "compName" in args:
        #用户名查找用户          
        projec_obj  =userC.checkProject(args["compName"])    
    return projec_obj

#检查用户输入
def checkInput(request):
    error_list={}
    error_str={'inputUsername':'该用户名已注册','mobile':'该手机已注册','inputEmail':'该邮箱已注册','compName':'该公司名已注册'}
    yzm=request.POST['mobile_yzm']
    yzm_session=get_session(request, 'msg')
    if(yzm_session!=yzm):
        error_list['mobile_yzm']='验证码失效或错误' 
    for key,value in request.POST.items():
        if(key=='inputUsername' or key=='mobile' or key=='inputEmail' or key=='compName'):
            args={} 
            args[key]=value
            if(checkuser(args)):
                error_list[key]=error_str[key] 
    return error_list
        

def update_garanted(signature, username):
    result = {'error_log': "", 'garanted': False}
    args = {'inputUsername': username}
    user_obj = checkuser(args)
    user_signature = user_obj[0].signature
    user_expire = user_obj[0].expire
    now = int(time.time())
    if now < user_expire:
        if signature == user_signature:
            result['garanted'] = True
        else:
            result['error_log'] = "认证失败：随机签名不正确"
    else:
        result['error_log'] = "认证失败：链接已过期，请重新生成"
    result['user'] = user_obj
    return result


'''
  正则匹配邮箱地址
  参  数： email  邮箱
  返回值： True／False
'''
def checkemail(email):
    p1=re.compile('[^\._-][\w\.-]+@(?:[A-Za-z0-9]+\.)+[A-Za-z]')
    emailmatch = p1.match(email)
    if emailmatch:
        return True
    else:
        return False
    
'''
    正则匹配电话号码
    参数：phone 手机号 
    返回：Ture／False
'''    
def checkTelephone(phone):
    p2=re.compile('^0\d{2,3}\d{7,8}$|^1[3578]\d{9}$|^147\d{8}')
    phonematch=p2.match(phone)
    if phonematch:
        return  True
    else:
        return  False

def set_session(request,key,val,timeout=300):
    if key and val:
        request.session[key] = val
        request.session[key+"outtime"] = time.time()+timeout
        return "ok"
    else:
        return "fail" 

    
def get_session(request,key):
    if key:
        if request.session.has_key(key):
            val=request.session.get(key,default=None)
            val_timeout=request.session[key+"outtime"]
            if(val_timeout<time.time()):
                request.session[key] =None
                return ""
            return val
        else:
            return None
    else:
        return None  

# 验证域名注册功能    
def checkHostFunction(request):
    currentHost='ON'
    if settings.REGISTER_STATUE is 'ON':
        host = request.get_host()
        host_list=host.split(':')
        host=host_list[0]
        hostmanage=settings.HOSTMANAGE
        if hostmanage.has_key(host):
            currentHost=hostmanage[host]['regiser_status']
    else:
        currentHost=settings.REGISTER_STATUE
    return currentHost
