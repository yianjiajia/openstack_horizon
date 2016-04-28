# --*-- coding:utf-8 --*--
__author__ = 'nolan'

import uuid
from hashlib import md5
from openstack_dashboard.api.member.member import *
import time
import hashlib 



def get_user(user_email):
    userC = UserCenter()
    param = {}
    param["email"]=user_email
    user = userC.checkUser(param)
    return user

# 数字签名
def create_signature(user, expire):
    username = user[0].name
    random_key = uuid.uuid4().__str__()
    signature=getMD5(str(username)+str(expire)+random_key)
    return signature


# 生成找回密码URL
def create_url(user,signature):
    # 有效时间30分钟
    username = user[0].name
    url = "/getpassword/" + "?sid=" + signature + "&username=" + username
    return url


# 保存参数
def save_param(user, signature, expire):
    userC = UserCenter()
    uid = user[0].id
    param = {}
    param["signature"] = signature
    param["expire"] = expire
    result=userC.updateUser(uid, param)
    print result
# 生成 MD5    
def getMD5(str):
    m2 = hashlib.md5()   
    m2.update(str)
    return m2.hexdigest()    

    
  


