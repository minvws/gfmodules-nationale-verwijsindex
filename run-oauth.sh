#!/bin/sh

# Generate a JWT for EPD1 LDN, signed by EPD-uzi certificate
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

# Get OAuth token using the generated JWT and mTLS client cert
BEARER=$(curl -X POST \
    localhost:8501/oauth/token \
    -H "Content-Type: application/x-www-form-urlencoded" \
    --data-urlencode "grant_type=client_credentials" \
    --data-urlencode "client_assertion_type=urn:ietf:params:oauth:client-assertion-type:jwt-bearer" \
    --data-urlencode "client_assertion=$JWT" \
    -H "x-proxy-ssl_client_verify: SUCCESS" \
    -H "x-proxy-ssl_client_cert: $CERT" | jq -r '.access_token')

# Access protected resource using the obtained OAuth token and mTLS client cert
curl -X GET \
    localhost:8501/registrations/test \
    -H "Authorization: bearer $BEARER" \
    -H "x-proxy-ssl_client_verify: SUCCESS" \
    -H "x-proxy-ssl_client_cert: $CERT"
