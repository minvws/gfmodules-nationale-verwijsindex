#!/bin/bash

# Generates dummy CA, Intermediates and client certificates used for testing LDN TLS connections.

openssl req -x509 -newkey rsa:2048 -sha256 -days 3650 -nodes \
  -keyout ca.ldn.key -out ca.ldn.crt \
  -subj "/C=NL/O=ca.ldn/CN=ca.ldn Root CA" \
  -addext "basicConstraints=critical,CA:TRUE" \
  -addext "keyUsage=critical,keyCertSign,cRLSign" \
  -addext "subjectKeyIdentifier=hash"

openssl req -newkey rsa:2048 -sha256 -nodes -keyout im1.ldn.key -out im1.ldn.csr -subj "/C=NL/O=im1.ldn/CN=im1.ldn Intermediate CA" && \
openssl x509 -req -in im1.ldn.csr -CA ca.ldn.crt -CAkey ca.ldn.key -CAcreateserial -out im1.ldn.crt -days 1825 -sha256 \
-extfile <(printf "basicConstraints=critical,CA:TRUE,pathlen:0\nkeyUsage=critical,keyCertSign,cRLSign\nauthorityKeyIdentifier=keyid,issuer\nsubjectKeyIdentifier=hash\n")

openssl req -newkey rsa:2048 -sha256 -nodes -keyout im2.ldn.key -out im2.ldn.csr -subj "/C=NL/O=im2.ldn/CN=im2.ldn Intermediate CA" && \
openssl x509 -req -in im2.ldn.csr -CA ca.ldn.crt -CAkey ca.ldn.key -CAserial ca.ldn.srl -out im2.ldn.crt -days 1825 -sha256 \
-extfile <(printf "basicConstraints=critical,CA:TRUE,pathlen:0\nkeyUsage=critical,keyCertSign,cRLSign\nauthorityKeyIdentifier=keyid,issuer\nsubjectKeyIdentifier=hash\n")

# epd-1 + epd-2 signed by im1
for n in 1 2; do openssl req -newkey rsa:2048 -sha256 -nodes -keyout epd-$n.ldn.key -out epd-$n.ldn.csr -subj "/C=NL/O=epd-$n.ldn/CN=epd-$n.ldn" && \
openssl x509 -req -in epd-$n.ldn.csr -CA im1.ldn.crt -CAkey im1.ldn.key -CAcreateserial -out epd-$n.ldn.crt -days 825 -sha256 \
-extfile <(printf "basicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature,keyEncipherment\nextendedKeyUsage=serverAuth,clientAuth\nsubjectAltName=DNS:epd-$n.ldn\n"); done

# epd-3 + epd-4 signed by im2
for n in 3 4; do openssl req -newkey rsa:2048 -sha256 -nodes -keyout epd-$n.ldn.key -out epd-$n.ldn.csr -subj "/C=NL/O=epd-$n.ldn/CN=epd-$n.ldn" && \
openssl x509 -req -in epd-$n.ldn.csr -CA im2.ldn.crt -CAkey im2.ldn.key -CAcreateserial -out epd-$n.ldn.crt -days 825 -sha256 \
-extfile <(printf "basicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature,keyEncipherment\nextendedKeyUsage=serverAuth,clientAuth\nsubjectAltName=DNS:epd-$n.ldn\n"); done
