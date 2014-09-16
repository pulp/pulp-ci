#!/bin/bash
set -x

# create/migrate pulp_database
# runuser apache -s /bin/bash /bin/bash -c "/usr/bin/pulp-manage-db"

if [ -z "$APACHE_HOSTNAME" ]
then
    echo "missing required environment variable APACHE_HOSTNAME"
    exit 2
fi


export OPENSSL_CONF=/root/ssl.conf

KEY_PATH=/etc/pki/tls/private
KEY_FILE=$KEY_PATH/pulp.key

CERT_PATH=/etc/pki/tls/certs
CERT_FILE=$CERT_PATH/pulp.crt
CSR_FILE=$CERT_PATH/pulp.csr

HTTPD_CONF=/etc/httpd/conf/httpd.conf
SSL_CONF=/etc/httpd/conf.d/ssl.conf

sed -i -e "s/^#ServerName www.example.com:80.*/ServerName $APACHE_HOSTNAME:80/" $HTTPD_CONF


configure_openssl() {
cat > $OPENSSL_CONF <<EOF
[ req ]
prompt                  = no
distinguished_name      = pulp_server

[ pulp_server ]
commonName              = $APACHE_HOSTNAME
stateOrProvinceName     = MA
countryName             = US
emailAddress            = admin@example.com
organizationName        = pulp
organizationalUnitName  = dev
EOF
}

# create and configure SSL certs for run-time hostname
create_ssl_cert() {
    openssl genrsa -out $KEY_FILE 2048
    openssl req -new -key $KEY_FILE -out $CSR_FILE
    openssl x509 -req -days 1095 -in $CSR_FILE -signkey $KEY_FILE -out $CERT_FILE
}

configure_ssl() {
    # use alternate substitute delimiter because the pattern contains /
    sed -i -e "s|^SSLCertificateFile .*|SSLCertificateFile $CERT_FILE|" $SSL_CONF
    sed -i -e "s|^SSLCertificateKeyFile .*|SSLCertificateKeyFile $KEY_FILE|" $SSL_CONF
    sed -i -e "s/^#ServerName www.example.com:443.*/ServerName $APACHE_HOSTNAME:443/" $SSL_CONF
}

configure_openssl
create_ssl_cert
configure_ssl

#exec /usr/sbin/init
exec /usr/sbin/httpd -DFOREGROUND -E -
