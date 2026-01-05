#!/bin/sh

CLIENT_CERT="epd-1.ldn.crt"

poetry run python generate-oauth-jwt.py \
    --mtls-cert secrets/${CLIENT_CERT} \
    --signing-cert secrets/epd-uzi.crt \
    --signing-key secrets/epd-uzi.key \
    --expires-in 86400 \
    --include-x5c \
    --token-url 'http://localhost:8501/oauth/token' \
    --out test.jwt

JWT=$(tr -d '\n' < ./test.jwt)
CERT=$(tr -d '\n' < ./secrets/${CLIENT_CERT})

curl -X POST \
    localhost:8501/oauth/token \
    -H "Content-Type: application/x-www-form-urlencoded" \
    --data-urlencode "grant_type=client_credentials" \
    --data-urlencode "client_assertion_type=urn:ietf:params:oauth:client-assertion-type:jwt-bearer" \
    --data-urlencode "client_assertion=$JWT" \
    -H "x-proxy-ssl_client_verify: SUCCESS" \
    -H "x-proxy-ssl_client_cert: $CERT"
