# OAuth within the NVI

There are two types of clients that can connect to the NVI: Clients with a UZI Server certificate and clients with an
LDN certificate. The MTLS setup will accept both certificate CAs.

A UZi Server certificate contains an URA number (the UZI subscriber number). It is enough to identify the clients of
the NVI.

However, the LDN server certificates do not have any URA numbers. Therefore, we must somehow "enrich" a connection made
with a LDN server with a URA number.

To do this, and to make sure we can accept different types of identification later on, we use OAuth for this. First, a
client with a UZI Server certificate will create a JWT token containing information about the client (the URA number).
This token is then sent to the NVI by the LDN client with only the LDN client certificate to the /oauth/token endpoint.

The NVI will validate if the JWT token is signed by a UZI Server client, and will return an OAuth token that the LDN
client can use for accessing the rest of the NVI services. The OAuth token will contain the URA number from the JWT
token so we can identify the clients' URA number without having an actual UZI server certificate.

Clients that want to connect to the NVI with a UZI Server certificate must also use the /oauth/token endpoint to collect
a valid OAUth token. However, these clients will not need to send a JWT token, as we can extract the URA number
directly from the UZI Server certificate.

From all other endpoints in the NVI, the OAuth token must be sent in the Authorization header as a Bearer token from
which the URA number can be extracted independent of certificate type used in the MTLS connection.

## Debugging

It's possible to disable the OAuth flow for debugging purposes. This is dune by setting the config setting
`oauth.enabled` to `false`. When this setting is disabled, you MUST set the `override_authentication_ura` to a valid
URA number that will be used for all requests. This is of course only for debugging and MUST NOT be used in
production.

Quick overview of the settings:

```ini
    [oauth]
    enabled = False
    override_authentication_ura = 87654321
    token_lifetime_seconds = 3600
    ca_cert = secrets/uzi-server-ca.crt
    ldn_ca_cert = secrets/ldn-chain.crt
    uzi_ca_cert = secrets/uzi-server-ca.crt
```

- `enabled`: If false, OAuth authentication is disabled and all requests will be authenticated with the URA number
  specified in `override_authentication_ura`.
- `override_authentication_ura`: The URA number to use when OAuth is disabled.
- `token_lifetime_seconds`: The lifetime of the OAuth tokens issued by the NVI.
- `ca_cert`: The CA certificate used to validate UZI Server certificates.
- `ldn_ca_cert`: The CA certificate used to validate LDN certificates.
- `uzi_ca_cert`: The CA certificate used to validate UZI Server certificates.

### JWT token

There is a `generate-oauth-jwt.py` helper that creates a JWT token signed with a UZI Server certificate.

The JWT header looks like this:

```json

{
  "typ": "JWT",
  "alg": "RS256",
  "kid": "BASE64URL(SHA-256( DER(signing_cert) ))",
  "x5c": [
    "BASE64(DER(signing_cert))"
  ]
}
```

The payload looks like this:

```json
{
{
  "iss": "URA_NUMBER",
  "sub": "URA_NUMBER",
  "aud": "https://example.com/oauth/token",
  "iat": 1700000000,
  "exp": 1700000300,
  "jti": "550e8400-e29b-41d4-a716-446655440000",
  "cnf": {
    "x5t#S256": "BASE64URL(SHA-256(DER(mtls_cert)))"
  }
}
```

Both the `issuer` (`iss`) and `subject` (`sub`) fields must contain the URA number of the UZI Server client creating
the JWT token. The audienence (`aud`) field must contain the URL of the token endpoint. This JWT can ONLY be exchanged
at that specific endpoint.

The `jti` will protected against replay attacks, and should be a unique value for each JWT token created.

The `cnf` field contains a confirmation claim that binds the JWT token to the MTLS certificate used by the LDN client.
This means that the JWT token can ONLY be exchanged by the LDN client that has the private key for the MTLS certificate
specified in the `cnf` claim.
