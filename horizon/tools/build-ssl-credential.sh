#!/bin/bash
if [ -z $1 ]
then
	echo "Usage: build-ssl-credential /home/workspace/ssl_keys"
        exit 1
fi

export EASY_RSA="`pwd`"
export KEY_CONFIG=`/usr/share/easy-rsa/whichopensslcnf /usr/share/easy-rsa/`
export OPENSSL="openssl"
export PKCS11TOOL="pkcs11-tool"
export GREP="grep"
export KEY_DIR="$EASY_RSA/keys"
export PKCS11_MODULE_PATH="dummy"
export PKCS11_PIN="dummy"
export KEY_SIZE=1024
export CA_EXPIRE=3650
export KEY_EXPIRE=3650
export KEY_COUNTRY="CN"
export KEY_PROVINCE="SH"
export KEY_CITY="ShangHai"
export KEY_ORG="Syscloud"
export KEY_EMAIL="admin@syscloud.cn"
export KEY_OU="cloud.syscloud.cn"
export KEY_NAME="VPN"

if [ ! -f /usr/share/easy-rsa/pkitool ]
then
    \cp /usr/share/easy-rsa/2.0/* /usr/share/easy-rsa/
    \cp /usr/share/easy-rsa/2.0/openssl-1.0.0.cnf /usr/share/easy-rsa/openssl.cnf
fi

KEY_DIR=$1 && \
rm -rf "$KEY_DIR" && \
mkdir -p "$KEY_DIR" && \
        chmod go-rwx "$KEY_DIR" && \
        touch "$KEY_DIR/index.txt" && \
        echo 01 >"$KEY_DIR/serial" && \
"/usr/share/easy-rsa/pkitool" --initca && \
"/usr/share/easy-rsa/pkitool" --server server && \
$OPENSSL dhparam -out ${KEY_DIR}/dh${KEY_SIZE}.pem ${KEY_SIZE} && \
"/usr/share/easy-rsa/pkitool" client

