# Interface Specification - Localization

## Summary

Localization is the process where a requester (healthcare provider) wants to determine which sources hold
data for a specific patient.
This is usually done in EPD's and PACS when a healthcare provider
wants to retrieve data for a patient from other healthcare providers.

The requester first retrieves a pseudonym for a personal identifier, such as a BSN, via the pseudonym service (PRS)
and then uses it in the localization request to the NVI.
The NVI performs an authorization check, decrypts the pseudonym,
matches it against registrations, and returns the sources that hold data for the patient in the specified care context.

![lookup process](../images/structurizr-LocalizeInterface.svg)

## Process

This interface is used in the following processes:

- [Localize health data](https://github.com/minvws/gfmodules-coordination/blob/main/docs/processes/localize_health_data.md)
- [Fetch timeline](https://github.com/minvws/gfmodules-coordination/blob/main/docs/processes/timeline.md)

### Steps in the localization process

1. The requester retrieves a pseudonym for the patient (via the pseudonym service).
2. The requester sends the encrypted pseudonym + own URA number + care context +
  optional filter on provider type(s) to the NVI.
3. The NVI performs an authorization and authentication check.
4. The NVI decrypts the pseudonym.
5. The NVI applies the filter on pseudonym, care context, provider type(s) (if specified) and looks for matches in registrations.
6. The NVI returns a list of sources.

## Authentication

Localization requires OAuth 2.0 and mTLS. See
[docs/interface-definitions/authorization.md](docs/interface-definitions/authorization.md).

## Endpoints

The following endpoints are provided:

- [Localize Organizations](#localize-organizations)

<div style="page-break-after: always;"></div>

### Localize Organizations

This endpoint localizes organizations (sources) that hold referrals/registrations
for a given pseudonym, care context and provider type(s).

| | |
| --- | --- |
| Path | /Organization/$localize |
| Type | POST |
| Query Parameters | None |
| Content-Type | application/fhir+json |
| Payload | [FHIR Parameters](#fhir-parameters) |

Example CURL request:

```curl
curl -X 'POST' \
  'https://nvi/Organization/$localize' \
  -H 'accept: application/fhir+json' \
  -H 'Content-Type: application/fhir+json' \
  -H 'Authorization: Bearer <<access_token>>' \
  -d '{
  "resourceType": "Parameters",
  "parameter": [
    {
      "name": "pseudonym",
      "valueString": "<<encrypted-pseudonym-jwe>>"
    },
    {
      "name": "oprfKey",
      "valueString": "<<base64-encoded-oprf-key>>"
    },
    {
      "name": "careContext",
      "valueCoding": {
        "system": "https://example.org/fhir/CodeSystem/care-context",
        "code": "MedicationAgreement",
        "display": "Medicatieafspraak"
      }
    },
    {
      "name": "filterOrgType",
      "valueCode": "apotheek"
    }
  ]
}'
```

Example response:

```json
{
  "resourceType": "Bundle",
  "type": "searchset",
  "timestamp": "2024-12-08T14:35:22Z",
  "total": 2,
  "entry": [
    {
      "resource": {
        "resourceType": "Organization",
        "id": "90000001",
        "identifier": [
          {
            "system": "https://example.org/fhir/NamingSystem/source",
            "value": "90000001"
          }
        ]
      }
    },
    {
      "resource": {
        "resourceType": "Organization",
        "id": "90000002",
        "identifier": [
          {
            "system": "https://example.org/fhir/NamingSystem/source",
            "value": "90000002"
          }
        ]
      }
    }
  ]
}
```

#### FHIR Parameters

The payload is a FHIR `Parameters` resource with the following parameters:

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| pseudonym | valueString | Yes | Encrypted pseudonym (JWE) issued by the pseudonym service. |
| oprfKey | valueString | Yes | Base64-encoded OPRF key associated with the pseudonym. |
| careContext | valueCoding | Yes | Care context in which localization is performed. |
| filterOrgType | valueCode | No | Filter on provider type(s). If specified, only sources of these types are returned. |

#### Pseudonym

The pseudonym is provided as an encrypted JWE in `Parameters.parameter[name="pseudonym"].valueString`.
The NVI decrypts the pseudonym internally and uses the decrypted value for matching.

#### OPRF key

The OPRF key is provided in `Parameters.parameter[name="oprfKey"].valueString` and is used to exchange the
pseudonym (PRS exchange) before matching occurs.

#### Care context

The care context is provided as `valueCoding` in `Parameters.parameter[name="careContext"]`. The code
defines the care context type (for example, `MedicationAgreement`).
The provided value needs to match any value in the system defined for care contexts.

#### Provider type filter

If `filterOrgType` is specified, the NVI applies this filter before returning results.
The filter value is a `valueCode` with the provider type (for example, `apotheek`).
The provided value needs to match any value in the system defined for provider types.

#### Response

The response is a FHIR `Bundle` of type `searchset` containing `Organization` resources that represent the
found sources. Each `Organization.identifier` contains the source's URA number and the source system.
