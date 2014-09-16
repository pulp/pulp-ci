#!/bin/bash

set -x

APACHE_HOSTNAME=${APACHE_HOSTNAME:=pulp.example.com}


configure_ssl_ca() {
    # $1=OPENSSL_CONF
    # $2=APACHE_HOSTNAME
    cat > $1 <<EOF
[ req ]
prompt                  = no
distinguished_name      = pulp_server

[ pulp_server ]
commonName              = $2
stateOrProvinceName     = MA
countryName             = US
emailAddress            = admin@example.com
organizationName        = pulp
organizationalUnitName  = dev
EOF
}


create_server_cert() {
    # create and configure SSL certs for run-time hostname
    CERT_PATH=${CERT_PATH:="/etc/pki/pulp"}

    SERVER_KEY_FILE=${SERVER_KEY_FILE:=${CERT_PATH}/server.key}
    CERT_REQUEST_FILE=${CERT_REQUEST_FILE:=${CERT_PATH}/server.csr}
    SERVER_CERT_FILE=${SERVER_CERT_FILE:=${CERT_PATH}/server.pem}
    CA_KEY_FILE=${CA_KEY_FILE:=${CERT_PATH}/ca.key}
    CA_CERT_FILE=${CA_CERT_FILE:=${CERT_PATH}/ca.crt}

    openssl genrsa -out ${SERVER_KEY_FILE} 2048
    openssl req -new -key ${SERVER_KEY_FILE} -out ${CERT_REQUEST_FILE}
    openssl x509 -req -days 365 -CA ${CA_CERT_FILE} -CAkey ${CA_KEY_FILE} \
        -set_serial 01 -in ${CERT_REQUEST_FILE} -out ${SERVER_CERT_FILE}
    
}

configure_httpd_ssl() {
    # HTTPD_SSL_CONF=$1
    sed -i "s|SSLCertificateFile /etc/pki/tls/certs/localhost.crt|SSLCertificateFile ${SERVER_CERT_FILE}|" ${HTTPD_SSL_CONF}
    sed -i "s|SSLCertificateKeyFile /etc/pki/tls/private/localhost.key|SSLCertificateKeyFile ${SERVER_KEY_FILE}|" ${HTTPD_SSL_CONF}
    sed -i "s/#ServerName www.example.com:443/ServerName ${APACHE_HOSTNAME}:443/" ${HTTPD_SSL_CONF}
}

# Take settings from Kubernetes service environment unless they are explicitly
# provided
PULP_SERVER_CONF=${PULP_SERVER_CONF:=/etc/pulp/server.conf}

PULP_SERVER_NAME=${PULP_SERVER_NAME:=pulp.example.com}

DB_SERVER_HOST=${DB_SERVER_HOST:=${SERVICE_HOST}}
DB_SERVER_PORT=${DB_SERVER_PORT:=27017}

MSG_SERVER_HOST=${MSG_SERVER_HOST:=${SERVICE_HOST}}
MSG_SERVER_PORT=${MSG_SERVER_PORT:=5672}

check_config_target() {
    if [ ! -f ${PULP_SERVER_CONF} ]
    then
        echo "Cannot find required config file ${PULP_SERVER_CONF}"
        exit 2  
    fi
}

#
# Set the Pulp service public hostname
#
configure_server_name() {
    sed -i -e "s/%PULP_SERVER_NAME%/${PULP_SERVER_NAME}/" ${PULP_SERVER_CONF}
}

#
# Set the messaging server access information
#
configure_messaging() {
    sed -i \
        -e "s/%MSG_SERVER_HOST%/${MSG_SERVER_HOST}/" \
        -e "s/%MSG_SERVER_PORT%/${MSG_SERVER_PORT}/" \
        $PULP_SERVER_CONF
}

#
# Set the database access information
#
configure_database() {
    sed -i \
        -e "s/%DB_SERVER_HOST%/${DB_SERVER_HOST}/" \
        -e "s/%DB_SERVER_PORT%/${DB_SERVER_PORT}/" \
        $PULP_SERVER_CONF
}

#========================================================================
# Main
#========================================================================
export OPENSSL_CONF=${OPENSSL_CONF:=/root/ssl.conf}
configure_ssl_ca ${OPENSSL_CONF} ${APACHE_HOSTNAME}
create_server_cert
unset OPENSSL_CONF

HTTPD_SSL_CONF=${HTTPD_SSL_CONF:=/etc/httpd/conf.d/ssl.conf}
configure_httpd_ssl ${HTTPD_SSL_CONF}

configure_messaging
configure_database

exec /usr/sbin/httpd -DFOREGROUND -E -
