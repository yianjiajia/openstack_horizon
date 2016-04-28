#coding=utf-8
from SMSSDK.CCPRestSDK import REST
import ConfigParser
from django.conf import settings

message_config= settings.MESSAGE
accountSid=message_config["accountSid"]
accountToken= message_config["accountToken"]
appId=message_config["appId"]
serverIP=message_config["serverIp"]
serverPort=message_config["serverPort"]
softVersion=message_config["softVersion"]

# 发送短信
# @param to      
# @param datas   
# @param tempId  
def sendTemplateSMS(to,datas,tempId=None):
    if tempId is None:
        tempId=message_config["tempId"]
    rest = REST(serverIP,serverPort,softVersion)
    rest.setAccount(accountSid,accountToken)
    rest.setAppId(appId)
     
    result = rest.sendTemplateSMS(to,datas,tempId)
    for k,v in result.iteritems(): 
         
        if k=='templateSMS' :
                for k,s in v.iteritems(): 
                    return '%s:%s' % (k, s)
        else:
            return '%s:%s' % (k, v)
            
# @param verifyCode 
# @param playTimes  
# @param to         
# @param displayNum 
# @param respUrl    
# @param lang       
# @param userData  
def voiceVerify(verifyCode,playTimes,to,displayNum,respUrl,lang,userData):
    rest = REST(serverIP,serverPort,softVersion)
    rest.setAccount(accountSid,accountToken)
    rest.setAppId(appId)
    
    result = rest.voiceVerify(verifyCode,playTimes,to,displayNum,respUrl,lang,userData)
    for k,v in result.iteritems(): 
        
        if k=='VoiceVerify' :
                for k,s in v.iteritems(): 
                    print '%s:%s' % (k, s)
        else:
            print '%s:%s' % (k, v)     
      
#sendTemplateSMS('18721400263',{'12345','5'},message_config["tempId"])