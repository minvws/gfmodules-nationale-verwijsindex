#! /bin/bash
set -e

URA_NUMBER=$1

echo "Creating certificate with ura number: ${URA_NUMBER}"

SCRIPT=$(readlink -f "$0")
TESTDIR=$(dirname "${SCRIPT}")/../tests/secrets

if [ ! -d "$TESTDIR" ]; then
  mkdir -p "$TESTDIR"
fi

openssl req -x509 \
  -nodes \
  -keyout "$TESTDIR"/dummy.key \
  -newkey rsa:1024 \
  -out "$TESTDIR"/mock-server-cert.crt \
  -days 3650 \
  -subj "/C=NL/O=MockTest Cert/CN=test.example.org/serialNumber=1234ABCD" \
  -addext "subjectAltName = otherName:2.5.5.5;IA5STRING:2.16.528.1.1003.1.3.5.5.2-1-12345678-S-$URA_NUMBER-00.000-00000000"
