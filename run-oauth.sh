#!/bin/sh

poetry run python generate-oauth-jwt.py \
    --client-id=ura:12341234 \
    --mtls-cert secrets/otv-stub.crt \
    --signing-cert secrets/nvi.crt \
    --signing-key secrets/nvi.key \
    --expires-in 86400 \
    --include-x5c \
    --scope nvi:read \
    --token-url 'http://localhost:8501/oauth/token' \
    --out test.jwt


JWT=$(tr -d '\n' < ./test.jwt)
CERT=$(tr -d '\n' < ./secrets/otv-stub.crt)

curl -X POST \
    localhost:8501/oauth/token \
    -H "Content-Type: application/x-www-form-urlencoded" \
    --data-urlencode "grant_type=client_credentials" \
    --data-urlencode "client_assertion_type=urn:ietf:params:oauth:client-assertion-type:jwt-bearer" \
    --data-urlencode "client_assertion=$JWT" \
    -H "x-proxy-ssl_client_verify: SUCCESS" \
    -H "x-proxy-ssl_client_cert: $CERT"
