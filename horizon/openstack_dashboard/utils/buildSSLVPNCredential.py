'''
Created on 2014.7.23

@author: alex
'''

import subprocess
from mako.template import Template
from StringIO import StringIO

def createKeys(keyBasePath):
    p = subprocess.Popen("/usr/bin/build-ssl-credential "+keyBasePath, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    exitCode=p.wait()
    if exitCode==0:
#         temp = Template(filename=basePath+"/server.conf")
#         content = temp.render( KEY_DIR=keyBasePath )
#         writeContent(keyBasePath+"/server.conf", content)
        
        return True
    else:
        while True:
            buff = p.stdout.readline()
            if buff == '' and p.poll() != None:
                break
            print buff
        return False

def createOvpn(serverAddr, basePath, keyBasePath):
    temp = Template(filename=basePath+"/client.ovpn")
    ovpnContent = temp.render(
                      server_addr=serverAddr,  
                      ca_crt_CONTENT=getContent(keyBasePath+"/ca.crt"), 
                      client_crt_CONTENT=getContent(keyBasePath+"/client.crt"), 
                      client_key_CONTENT=getContent(keyBasePath+"/client.key")
                      )
    writeContent(keyBasePath+"/client.ovpn", ovpnContent)
    
def writeContent(path, content):
    f = file(path, 'w')
    f.write(content)
    f.close()

def getContent(path):
    buf = StringIO()
    f = file(path,'r')
    lines = f.readlines()
    buf.writelines(lines)
    return buf.getvalue().strip()

if __name__ == '__main__':
    keyBasePath='/tmp/keys'
    createKeys(keyBasePath)
#     basePath='/home/alex/workspace/openvpn/'
#     subnet="10.0.0.0 255.255.255.0"
#     createOvpn("192.168.210.110", basePath, keyBasePath)
