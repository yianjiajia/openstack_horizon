# --*-- coding: utf-8 --*--
__author__ = 'nolan'


from email import encoders
from email.header import Header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from django.conf import settings

from email.utils import parseaddr, formataddr
import smtplib


#  格式化参数
def _format_addr(s):
    name, addr = parseaddr(s)
    return formataddr((\
        Header(name, 'utf-8').encode(),\
        addr.encode('utf-8') if isinstance(addr, unicode) else addr))


def sendmail(user_email, random_url,user):
    name=user[0].name
    # 设置参数
    from_addr = settings.EMAIL_HOST_USER
    password = settings.EMAIL_HOST_PASSWORD
    to_addr = user_email
    smtp_server = settings.EMAIL_HOST
    # 邮件头
    msg = MIMEMultipart('alternative')
    msg['From'] = _format_addr(u'SysCloud<%s>' % from_addr)
    msg['To'] = _format_addr(u'<%s>' % to_addr)
    msg['Subject'] = Header(u'重置密码', 'utf-8').encode()

    # 邮件正文是MIMEText:
    str='<html><body>亲爱的用户：<br>'
    str=str+'您好，您的注册账户:'+name+'<h1>请点击如下链接进行密码修改：</h1>'
    str=str+'<p><a href="'+random_url+'">' + random_url + '</a></p>'
    str=str+'</body></html>'
#     msg.attach(MIMEText('send with file...', 'plain', 'utf-8'))
#     msg.attach(MIMEText(''))
    msg.attach(MIMEText(str,'html','utf-8'))
               


    # 发送邮件
    try:
        server = smtplib.SMTP(smtp_server, 25)
        server.set_debuglevel(1)
        server.login(from_addr, password)
        server.sendmail(from_addr, [to_addr], msg.as_string())

        server.quit()
        return True

    except Exception, e:
        print str(e)
        return False
    