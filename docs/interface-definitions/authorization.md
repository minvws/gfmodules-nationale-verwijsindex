# Interface Authorization

## Overview

All endpoints except `/`, `/health`, `/version.json`, and `/fhir/metadata` require OAuth 2.0 authorization.
Clients must include a valid bearer token in the `Authorization` header.
Requests without a valid token are rejected.

## Requirements

- Obtain an access token from the authorized OAuth 2.0 authorization server.
- Include the header on every request:

```HTTP
Authorization: Bearer <access_token>
```

- The access token must be valid and not expired and must have the required scopes/claims
    for the requested resource.

## Relationship with mTLS

OAuth authorization is required in addition to mTLS. A valid UZI Server or LDN Certificate is still mandatory for
transport-level authentication.
