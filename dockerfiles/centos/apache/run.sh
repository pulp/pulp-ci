#!/bin/bash

# create/migrate pulp_database
runuser apache -s /bin/bash /bin/bash -c "/usr/bin/pulp-manage-db"

cat > /root/ssl.conf <<EOF
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

export OPENSSL_CONF=/root/ssl.conf

# create and configure SSL certs for run-time hostname
CERT_PATH="/etc/pki/pulp"
openssl genrsa -out $CERT_PATH/server.key 2048
openssl req -new -key $CERT_PATH/server.key -out $CERT_PATH/server.csr
openssl x509 -req -days 365 -CA $CERT_PATH/ca.crt -CAkey $CERT_PATH/ca.key -set_serial 01 -in $CERT_PATH/server.csr -out $CERT_PATH/server.crt

sed -i "s/SSLCertificateFile \/etc\/pki\/tls\/certs\/localhost.crt/SSLCertificateFile \/etc\/pki\/pulp\/server.crt/" /etc/httpd/conf.d/ssl.conf
sed -i "s/SSLCertificateKeyFile \/etc\/pki\/tls\/private\/localhost.key/SSLCertificateKeyFile \/etc\/pki\/pulp\/server.key/" /etc/httpd/conf.d/ssl.conf
sed -i "s/#ServerName www.example.com:443/ServerName $APACHE_HOSTNAME:443/" /etc/httpd/conf.d/ssl.conf 

exec /usr/sbin/init
