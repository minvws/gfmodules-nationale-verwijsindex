# Interface Specification National Referral Index - Update localization data

## Disclaimer

This project and all associated code serve solely as **documentation and demonstration purposes**
to illustrate potential system communication patterns and architectures.

This codebase:

- Is NOT intended for production use
- Does NOT represent a final specification
- Should NOT be considered feature-complete or secure
- May contain errors, omissions, or oversimplified implementations
- Has NOT been tested or hardened for real-world scenarios

The code examples are *only* meant to help understand concepts and demonstrate possibilities.

By using or referencing this code, you acknowledge that you do so at your own risk and that
the authors assume no liability for any consequences of its use.

This interface currently doesn't fully adhere to the
[NLGov REST API Design Rules](https://gitdocumentatie.logius.nl/publicatie/api/adr/) because it's still 'under
construction'.

## Context

The GFModules project is a collection of applications that have the purpose of improving data exchange process between
healthcare providers. The project is the technical implementation of various components of the 'Generieke Functies,
lokalisatie en addressering' project of the Ministry of Health, Welfare and Sport of the Dutch government.

The National Referral Index (NRI) is responsible for the referral of the Health Data. The NRI contains a referral
to the register that associates a Health Provider with pseudonym and data domain.

This interface description and other interfaces of this application can be found at the [github repository](https://github.com/minvws/gfmodules-national-referral-index/tree/feat/interface-description/docs/interface-definitions).

<div style="page-break-after: always;"></div>

## Summary

This interface enables applications in the Healthcare Provider domain to create or update the localized data that is
stored in the NRI based on a reference to a pseudonymised BSN (RID). This RID needs to be fetched first from the PRS
(see [Process](#process)).

![lookup process](../images/structurizr-UpdateLocalizationDataInterface.svg)

<div style="page-break-after: always;"></div>

## Process

This interface is used in the following processes:

- [Update localized health data](https://github.com/minvws/gfmodules-coordination/blob/main/docs/processes/update_localization_data.md)

## Authentication

All endpoints that are described here are only accessible behind mTLS with a valid UZI Server Certificate. The provided
URA number should also match the URA number from the certificate.

## Endpoints

The following endpoints are provided:

- [registrations (Post)](#registrations-post)
- [registrations/query (Post)](#registrationsquery-post)
- [registrations (Delete)](#registrations-delete)

<div style="page-break-after: always;"></div>

### registrations (Post)

The registrations (Post) endpoint creates a new referral for the provided parameters.

<!-- markdownlint-disable MD013 -->
| | |
| --- | --- |
| Path | /registrations |
| Type | POST |
| Query Parameters | None |
| JSON payload | [Pseudonym](#pseudonym), [DataDomain](#datadomain), [UraNumber](#uranumber), [RequestingUziNumber](#requestinguzinumber) |
| Response codes | 201, 422 |
<!-- markdownlint-enable MD013 -->

Example CURL request:

```curl
curl -X 'POST' \
  'https://referral-index/registrations' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "pseudonym": "<<pseudonym>>",
  "data_domain": "beeld",
  "ura_number": "<<ura_number>>",
  "requesting_uzi_number": "<<uzi_number>>"
}'
```

Example response:

```json
{
  "pseudonym": "<<pseudonym>>",
  "data_domain": "beeldbank",
  "ura_number": "13873620"
}
```

### registrations/query (Post)

The registrations/query (POST) endpoint returns the stored referrals for the client URA.

<!-- markdownlint-disable MD013 -->
| | |
| --- | --- |
| Path | /registrations/query |
| Type | POST |
| Query Parameters | None |
| JSON payload | [Pseudonym](#pseudonym) (Optional), [DataDomain](#datadomain) (Optional), [UraNumber](#uranumber), [RequestingUziNumber](#requestinguzinumber) |
| Response codes | 422 |
<!-- markdownlint-enable MD013 -->

Example CURL request:

```curl
curl -X 'POST' \
  'https://referral-index/registrations/query' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "pseudonym": "<<pseudonym>>",
  "data_domain": "beeld",
  "ura_number": "<<ura_number>>",
  "requesting_uzi_number": "<<uzi_number>>"
}'
```

Example response:

```json
[
  {
    "pseudonym": "<<pseudonym>>",
    "data_domain": "beeldbank",
    "ura_number": "13873620"
  }
]
```

### registrations (Delete)

The registrations (Delete) endpoint removes a referral for the provided parameters. This action is irreversible.
The registrations are actually deleted in the NRI register.

<!-- markdownlint-disable MD013 -->
| | |
| --- | --- |
| Path | /registrations |
| Type | DELETE |
| Query Parameters | None |
| JSON payload | [Pseudonym](#pseudonym), [DataDomain](#datadomain), [UraNumber](#uranumber), [RequestingUziNumber](#requestinguzinumber) |
| Response codes | 204, 404, 422 |
<!-- markdownlint-enable MD013 -->

Example CURL request:

```curl
curl -X 'DELETE' \
  'https://referral-index/registrations' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "pseudonym": "<<pseudonym>>",
  "data_domain": "beeld",
  "ura_number": "<<ura_number>>",
  "requesting_uzi_number": "<<uzi_number>>"
}'
```

Example response:

```json
{
  "pseudonym": "<<pseudonym>>",
  "data_domain": "beeldbank",
  "ura_number": "13873620"
}
```

#### Pseudonym

A pseudonym send as a query parameter or as a json property is always serialized as a string

TODO: Update pseudonym to RID when PRS implementation is finished

#### DataDomain

Currently the only supported data domain is `beeldbank`. More will be added in the future.

#### UraNumber

The URA number (UZI Register Abonneenummer) is a number that should match the provided mTLS client certificate. This is
to make sure that it's not possible to use a different certificate by accident when a client has multiple valid Server
Certificates.

#### RequestingUziNumber

The requesting UZI number is required to be able to log who the actual request did. This is required for auditing.
This parameter is likely to be changed to a Dezi token which can also be validated on the NRI.
