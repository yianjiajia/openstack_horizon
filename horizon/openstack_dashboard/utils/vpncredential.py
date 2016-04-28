'''
@author: alex
'''
import os
import re
import uuid
import subprocess
from StringIO import StringIO

from mako.template import Template

def createCredential(keyBasePath):
    p = subprocess.Popen("/usr/bin/build-ssl-credential "+keyBasePath, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    exitCode=p.wait()
    if exitCode==0:
        print "generated credential in %s" % keyBasePath
        return True
    else:
        while True:
            buff = p.stdout.readline()
            if buff == '' and p.poll() != None:
                break
            print buff
        return False

def cleanCredential(keyBasePath):
    pattern = re.compile(r'^/tmp/vpncredentials/.*')
    if pattern.match(keyBasePath):
        os.system("rm -rf %s" % keyBasePath)

def readFileContent(path):
    buf = StringIO()
    f = file(path,'r')
    lines = f.readlines()
    buf.writelines(lines)
    f.close()
    return buf.getvalue().strip()

def writeContent(path, content):
    f = file(path, 'w')
    f.write(content)
    f.close()
    return f

def renderOvpn(basePath, **kwargs):
    temp = Template(filename=basePath+"/client.ovpn.template")
    return temp.render(
        server_addr=kwargs['server_addr'] if kwargs.has_key('server_addr') else "",
        ca_crt_CONTENT=kwargs['ca_crt'] if kwargs.has_key('ca_crt') else "",
        client_crt_CONTENT=kwargs['client_crt'] if kwargs.has_key('client_crt') else "",
        client_key_CONTENT=kwargs['client_key'] if kwargs.has_key('client_key') else "",
        )

if __name__ == '__main__':
    temp_dir_id = uuid.uuid4().get_hex()
    createCredential("/tmp/"+temp_dir_id)
#     print renderOvpn("/etc/neutron")
