# -*- coding:utf-8 -*-
from django.shortcuts import render
from django.http import HttpResponseRedirect
from openstack_dashboard.settings import WEBROOT
from openstack_dashboard.notice.message.SendTemplateSMS import voiceVerify
from openstack_dashboard.notice.message.SendTemplateSMS import sendTemplateSMS
from openstack_dashboard.notice.email.sendEmail import sendmail
from openstack_dashboard.notice.email import createEmail
from django.http import HttpResponse
from openstack_dashboard.api.member.member import *
from django.conf import settings
import random
import validate
import time
import code
import json
from PIL import Image
import urllib
'''
 注册页面
 1:验证用户是否有“注册”功能
 2:验证用户是否登录
 3:验证是否数据提交
'''
def register(request): 

    loginurl=settings.LOGIN_URL
    regist_status=validate.checkHostFunction(request);
    if regist_status is not 'ON':
        return HttpResponseRedirect(settings.LOGIN_URL) 
    if request.method == 'POST': 
        
        host = request.get_host()
        refer=request.META.get('HTTP_REFERER',"/")
        proto, rest = urllib.splittype(refer)
        resRefer, rest = urllib.splithost(rest)
        settingRegisterUrl=settings.REGISTER_URL
        if not resRefer or resRefer!=host:
           errors={'inputUsername':'非法访问访问受限'}
           return  render(request, 'auth/register.html', locals())   

        
        form_val=request.POST
        errors=validate.checkInput(request)
        if errors:
            return  render(request, 'auth/register.html', locals())     
        user = {
                "name":request.POST.get('inputUsername'),
                "password":request.POST.get('password'),
                "telephone": request.POST.get('mobile'),
                "email":request.POST.get('inputEmail'),
                "company": request.POST.get('compName'),
                "industry": request.POST.get('industry'),
        }  
        userC = UserCenter()  
        name= request.POST.get('inputUsername')
        user['default_role_id'] = userC.get_default_role_id()
        user_obj=userC.createUser(user, request.get_host())
        registerurl=settings.REGISTER_URL
        
        request.session["safeCard"]=None 
        request.session["code"]=None 
        request.session["msg"]=None 
        request.session["code_mobile"]=None 
        request.session["sendmsTime"]=None 
        
        return  render(request, 'auth/register_status.html', locals())      
    else: 
        random_num=random.sample('0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ',12) 
        safeCard = ''.join(random_num)
        validate.set_session(request,'safeCard',safeCard)
        
        return  render(request, 'auth/register.html', locals())

        
#    ajax－查找用户 
#    session 验证随机编码
#    验证请求的网址
def ajaxCheckUser(request):
    #上一级url验证
    host = request.get_host()
    refer=request.META.get('HTTP_REFERER',"/")
    proto, rest = urllib.splittype(refer)
    resRefer, rest = urllib.splithost(rest)
    settingRegisterUrl=settings.REGISTER_URL
    if not resRefer or resRefer!=host:
        return HttpResponse('limitVisit')  

    #安全卡验证 
    safeCard=validate.get_session(request,'safeCard')
    inputsafeCard=''
    if 'inputsafeToken' in request.GET:
        inputsafeCard=request.GET['inputsafeToken']
        if not inputsafeCard:
            return HttpResponse('safeTokenError')
    else:
        return HttpResponse('safeTokenError')
    if safeCard is None:
        return HttpResponse('safeTokenTimeout')
    elif  safeCard!=inputsafeCard:
        return HttpResponse('safeTokenError')

    
    #数据查询
    
    if "mobile" in request.GET:
        mobile=request.GET["mobile"]
        code_mobile=validate.get_session(request, 'code_mobile')
        if code_mobile:
            if code_mobile!=mobile:
                request.session["msg"]=None 
                request.session["code_mobile"]=None
                
    result=validate.checkuser(request.GET)
    if len(result):
        return HttpResponse('Exist') 
    else: 
        return HttpResponse('NotExist') 
  
 
#    ajax－查找项目 
#    session 验证随机编码
#    验证请求的网址
def ajaxCheckProject(request):
    #上一级url验证
    host = request.get_host()
    refer=request.META.get('HTTP_REFERER',"/")
    proto, rest = urllib.splittype(refer)
    resRefer, rest = urllib.splithost(rest)
    settingRegisterUrl=settings.REGISTER_URL
    if not resRefer or resRefer!=host:
        return HttpResponse('limitVisit')  

    #安全卡验证 
    safeCard=validate.get_session(request,'safeCard')
    inputsafeCard=''
    if 'inputsafeToken' in request.GET:
        inputsafeCard=request.GET['inputsafeToken']
        if not inputsafeCard:
            return HttpResponse('safeTokenError')
    else:
        return HttpResponse('safeTokenError')
    if safeCard is None:
        return HttpResponse('safeTokenTimeout')
    elif  safeCard!=inputsafeCard:
        return HttpResponse('safeTokenError')
    #数据查询
    result=validate.checkproject(request.GET)
    if len(result):
        return HttpResponse('Exist') 
    else: 
        return HttpResponse('NotExist')  
  
  
        
#   browsers check         
def browsers(request):
    horizonWEBROOT=WEBROOT
    return  render(request, 'auth/browsers.html', locals())

#   找回密码第一步
def getpassword(request):  
    loginurl=settings.LOGIN_URL
    homeURl=loginurl.replace("/auth/login/","/")
    status = ""
    random_num=random.sample('0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ',12) 
    safeCard = ''.join(random_num)
    validate.set_session(request,'safeCard',safeCard)
    if "sid" in request.GET:
        signature = request.GET['sid']
        username = request.GET['username']
        validate_result = validate.update_garanted(signature, username)
        user = validate_result['user'][0]
        error=validate_result['error_log']
    return render(request, 'auth/getpassword.html', locals())


#   修改用户密码
def ajaxUpdatePassword(request):
    #上一级url验证
    host = request.get_host()
    refer=request.META.get('HTTP_REFERER',"/")
    proto, rest = urllib.splittype(refer)
    resRefer, rest = urllib.splithost(rest)
    settingRegisterUrl=settings.REGISTER_URL
    if not resRefer or resRefer!=host:
        return HttpResponse(json.dumps({'status':'FAIL','error':'limitVisit'}))

    #安全卡验证 
    safeCard=validate.get_session(request,'safeCard')
    inputsafeCard=''
    if 'inputsafeToken' in request.GET:
        inputsafeCard=request.GET['inputsafeToken']
    else:
        return HttpResponse(json.dumps({'status':'FAIL','error':'safeTokenError'})) 
    if safeCard is None:
        return HttpResponse(json.dumps({'status':'FAIL','error':'safeTokenTimeout'})) 
    elif  safeCard!=inputsafeCard:
        return HttpResponse(json.dumps({'status':'FAIL','error':'safeTokenError'})) 


    password=request.GET['password'];
    user_obj=validate.checkuser(request.GET)
    result={'status':'FAIL','user':''}
    if len(user_obj):
        args={'password':password}
        user=updateUser(user_obj[0].id,args)
        if user:
            result['status']='OK'
            result['user']={'name':user_obj[0].name,'mobile':user_obj[0].telephone,'email':user_obj[0].email}
    return HttpResponse(json.dumps(result)) 

  
#    修改用户信息
def updateUser(uid,args):
    userC = UserCenter()
    result=userC.updateUser(uid,args)
    if(result):
        return True
    else:
        return False

#   手机验证
def sendEmail(request):
    host = request.get_host()
    path = request.path
    status=''
    linkUrlBase="http://"+host+path.replace("/member/sendEmail/","")
    if 'email' in request.GET:
        email=request.GET['email']    
        expire = int(time.time() + 30*60)  # 有效时间30分钟
        args={'inputEmail':email}
        user =validate.checkuser(args)  # 获得用户
        if len(user):
            signature = createEmail.create_signature(user, expire)  # 生成数字签名
            random_url=createEmail.create_url(user, signature)  # 生成找回密码URL
            createEmail.save_param(user, signature, expire)  # 保存签名，时效
            send_status=sendmail(email,linkUrlBase+random_url,user)  # 发送重置密码邮件
            if send_status:
                status="OK"
            else:
                status = "FAIL"
    return HttpResponse(status)

#    生成图片验证码
def createCode(request):
    code_obj=code.createCode()
    validate.set_session(request,'code',code_obj['text'])
    response = HttpResponse(content_type="image/gif")
    image=code_obj['img']
    image.save(response, "gif")
    return response
#    核查图片验证码
def checkCode(request):
    host = request.get_host()
    refer=request.META.get('HTTP_REFERER',"/")
    proto, rest = urllib.splittype(refer)
    resRefer, rest = urllib.splithost(rest)
    settingRegisterUrl=settings.REGISTER_URL
    if not resRefer or resRefer!=host:
        return HttpResponse('limitVisit')  
    
    sessionCode=validate.get_session(request, 'code')
    if  sessionCode:
        sessionCode=sessionCode.lower()
    if ('code' in request.GET) and sessionCode:
        code=request.GET['code']
        result=''
        if code:
            if(sessionCode==code):
                result={'status':'OK','error':'','code':sessionCode}   
            else:
                result={'status':'FAIL','error':'验证码输入错误','code':sessionCode}   
        else:   
            result={'status':'FAIL','error':'验证码不能为空','code':sessionCode}     
    else:
        result={'status':'FAIL','error':'参数不能为空'}  
    return HttpResponse(json.dumps(result)) 


#    手机验证
def sendMsg(request):

     #上一级url验证
    host = request.get_host()
    refer=request.META.get('HTTP_REFERER',"/")
    proto, rest = urllib.splittype(refer)
    resRefer, rest = urllib.splithost(rest)
    settingRegisterUrl=settings.REGISTER_URL
    if not resRefer or resRefer!=host:
        return HttpResponse('limitVisit')  

    #安全卡验证 
    safeCard=validate.get_session(request,'safeCard')
    inputsafeCard=''
    if 'inputsafeToken' in request.GET:
        inputsafeCard=request.GET['inputsafeToken']
        if not inputsafeCard:
            return HttpResponse('safeTokenError')
    else:
        return HttpResponse('safeTokenError')
    if safeCard is None:
        return HttpResponse('safeTokenTimeout')
    elif  safeCard!=inputsafeCard:
        return HttpResponse('safeTokenError')
    
    #图片验证 check
    sessionCode=validate.get_session(request, 'code')
    if  not sessionCode:
        return HttpResponse("picCodeTimeout")
    elif ('code' in request.GET):
        sessionCode=sessionCode.lower()
        if(sessionCode!=request.GET['code']):
            return HttpResponse("picError")
        
    #短信发送间隔60秒
    sendmsTime=validate.get_session(request, 'sendmsTime')
    if sendmsTime:
        interval=time.time()-sendmsTime
        if interval<60:
            return HttpResponse("一分钟才能发一条短信哦")

    #发手机验证
    if 'mobile' in request.GET:
        telephone=request.GET['mobile']    
    random_num=random.sample('0123456789',6) 
    str = ''.join(random_num)
    if request.GET.get('type') == 'voice':
        voiceVerify(str,2,telephone,'','','','')
    else:
        sendTemplateSMS(telephone,[str,5]) 
    validate.set_session(request,'msg',str)
    #设置图片验证失效：
    code_num=random.sample('0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ',12) 
    code_num = ''.join(code_num)
    validate.set_session(request,'code_mobile',telephone)
    validate.set_session(request,'code',code_num)
    validate.set_session(request,'sendmsTime',time.time())
    logging.warning('yanzhengma : ------%s------' % str)
    return HttpResponse("ok")

#    核查短信验证码
def checkMsg(request):
    
    #上一级url验证
    host = request.get_host()
    refer=request.META.get('HTTP_REFERER',"/")
    proto, rest = urllib.splittype(refer)
    resRefer, rest = urllib.splithost(rest)
    settingRegisterUrl=settings.REGISTER_URL
    if not resRefer or resRefer!=host:
        return HttpResponse('limitVisit')  

    #安全卡验证 
    safeCard=validate.get_session(request,'safeCard')
    inputsafeCard=''
    if 'inputsafeToken' in request.GET:
        inputsafeCard=request.GET['inputsafeToken']
        if not inputsafeCard:
            return HttpResponse('safeTokenError')
    else:
        return HttpResponse('safeTokenError')
    if safeCard is None:
        return HttpResponse('safeTokenTimeout')
    elif  safeCard!=inputsafeCard:
        return HttpResponse('safeTokenError')
    
    
    
    sessionMsg=validate.get_session(request, 'msg')
    if 'msg' in request.GET:
        msg=request.GET['msg']
        result=''
        if msg:
            if not sessionMsg:
                result={'status':'FAIL','error':'验证码已失效,请重新发送'} 
            elif sessionMsg==msg:
                result={'status':'OK','error':''}   
            else:
                result={'status':'FAIL','error':'手机验证码输入错误'}   
        else:   
            result={'status':'FAIL','error':'手机验证码不能为空'}     
    else: 
        result={'status':'FAIL','error':'参数不能为空'}   
    return HttpResponse(json.dumps(result)) 
        



       

   
    
