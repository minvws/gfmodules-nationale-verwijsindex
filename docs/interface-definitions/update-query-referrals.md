# Interface Specification - Update/Query Referrals

## Summary

This interface enables applications in the Healthcare Provider domain to create, retrieve,
and delete referrals stored in the NVI.

![lookup process](../images/structurizr-UpdateLocalizationDataInterface.svg)

## Authentication

Updating or querying referrals requires OAuth 2.0 and mTLS. See
[docs/interface-definitions/authorization.md](docs/interface-definitions/authorization.md).

## Endpoints

The following endpoints are provided:

- [Create NVIDataReference](#create-nvidatareference)
- [Search NVIDataReference](#search-nvidatareference)
- [Delete NVIDataReference](#delete-nvidatareference)
- [Get NVIDataReference by ID](#get-nvidatareference-by-id)
- [Delete NVIDataReference by ID](#delete-nvidatareference-by-id)

<div style="page-break-after: always;"></div>

### Create NVIDataReference

Creates a new `NVIDataReference` resource for the provided subject and metadata.
If the resource already exists, the existing resource is returned with status 200.

| | |
| --- | --- |
| Path | /NVIDataReference |
| Type | POST |
| Query Parameters | None |
| Content-Type | application/fhir+json |
| Payload | [NVIDataReference Input](#nvidatareference-input) |

#### NVIDataReference Input

The payload is a FHIR `NVIDataReference` resource with the following required fields:

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| resourceType | string | Yes | Must be `NVIDataReference`. |
| subject | Identifier | Yes | Encrypted pseudonym (JWE) with system `subject`. |
| source | Identifier | Yes | Source organization URA number (must match OAuth token URA). |
| sourceType | CodeableConcept | Yes | Organization type (ValueSet nvi-organization-types). |
| careContext | CodeableConcept | Yes | Care context (ValueSet hcim-2024-zibs). |
| oprfKey | string | Yes | Base64-encoded OPRF key used for pseudonym exchange. |

Example CURL request:

```curl
curl -X 'POST' \
  'https://nvi/NVIDataReference' \
  -H 'accept: application/fhir+json' \
  -H 'Content-Type: application/fhir+json' \
  -H 'Authorization: Bearer <<access_token>>' \
  -d '{
  "resourceType": "NVIDataReference",
  "subject": {
    "system": "https://example.org/fhir/NamingSystem/subject",
    "value": "<<encrypted-pseudonym-jwe>>"
  },
  "source": {
    "system": "https://example.org/fhir/NamingSystem/source",
    "value": "90000001"
  },
  "sourceType": {
    "coding": [
      {
        "system": "https://example.org/fhir/CodeSystem/source-type",
        "code": "laboratorium"
      }
    ]
  },
  "careContext": {
    "coding": [
      {
        "system": "https://example.org/fhir/CodeSystem/care-context",
        "code": "LaboratoryTestResult"
      }
    ]
  },
  "oprfKey": "<<base64-encoded-oprf-key>>"
}'
```

Example response:

``` HTTP
Content-Type: application/fhir+json
Location: https://nvi/NVIDataReference/12345
```

Note: The `Location` header is only set on the first successful create (201).
The API is idempotent for repeated creates of the same referral and will return 200 with the existing resource.

```json
{
  "resourceType": "NVIDataReference",
  "id": "12345",
  "meta": {
    "versionId": "1",
    "lastUpdated": "2024-12-08T14:40:00Z"
  },
  "source": {
    "system": "https://example.org/fhir/NamingSystem/source",
    "value": "90000001"
  },
  "sourceType": {
    "coding": [
      {
        "system": "https://example.org/fhir/CodeSystem/source-type",
        "code": "laboratorium",
        "display": "Laboratorium"
      }
    ]
  },
  "careContext": {
    "coding": [
      {
        "system": "https://example.org/fhir/CodeSystem/care-context",
        "code": "LaboratoryTestResult",
        "display": "Laboratorium uitslag"
      }
    ]
  }
}
```

### Search NVIDataReference

Retrieves `NVIDataReference` resources based on query parameters.

| | |
| --- | --- |
| Path | /NVIDataReference |
| Type | GET |
| Query Parameters | [Query Parameters](#query-parameters) |
| Content-Type | application/fhir+json |

#### Query Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| source | string | Yes | URA number of the source organization. |
| pseudonym | string | No | Encrypted pseudonym (JWE). When combined with `oprfKey`, filters on a patient. |
| oprfKey | string | No | Base64-encoded OPRF key. Required when `pseudonym` is provided. |
| careContext | string | No | Care context code to filter results. |

#### Query Behavior

- If `pseudonym` and `oprfKey` are provided, the NVI exchanges the pseudonym and filters on the patient.
- If `careContext` is provided, the result set is filtered to that care context.

Example CURL request:

```curl
curl -X 'GET' \
  'https://nvi/NVIDataReference?source=90000001&careContext=LaboratoryTestResult&' \
  'pseudonym=<<encrypted-pseudonym-jwe>>&oprfKey=<<base64-encoded-oprf-key>>' \
  -H 'accept: application/fhir+json' \
  -H 'Authorization: Bearer <<access_token>>'
```

Example response:

``` HTTP
Content-Type: application/fhir+json
```

```json
{
  "resourceType": "Bundle",
  "type": "searchset",
  "timestamp": "2026-01-26T14:46:08.945612",
  "total": 1,
  "entry": [
    {
      "resource": {
        "resourceType": "NVIDataReference",
        "id": "12345",
        "meta": {
          "versionId": "1",
          "lastUpdated": "2024-12-08T14:40:00Z"
        },
        "source": {
          "system": "https://example.org/fhir/NamingSystem/source",
          "value": "90000001"
        },
        "sourceType": {
          "coding": [
            {
              "system": "https://example.org/fhir/CodeSystem/source-type",
              "code": "laboratorium",
              "display": "Laboratorium"
            }
          ]
        },
        "careContext": {
          "coding": [
            {
              "system": "https://example.org/fhir/CodeSystem/care-context",
              "code": "LaboratoryTestResult",
              "display": "Laboratorium uitslag"
            }
          ]
        }
      }
    }
  ]
}
```

### Delete NVIDataReference

Deletes `NVIDataReference` resources based on query parameters.

| | |
| --- | --- |
| Path | /NVIDataReference |
| Type | DELETE |
| Query Parameters | [Delete Query Parameters](#delete-query-parameters) |

#### Delete Query Parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| source | string | Yes | URA number of the source organization. |
| pseudonym | string | No | Encrypted pseudonym (JWE). When combined with `oprfKey`, filters on a patient. |
| oprfKey | string | No | Base64-encoded OPRF key. Required when `pseudonym` is provided. |
| careContext | string | No | Care context code to filter results. |

#### Deletion Behavior

- `DELETE /NVIDataReference` with only `source` deletes all registrations for the organization.
- `DELETE /NVIDataReference` with `pseudonym` and `oprfKey` deletes all registrations for the patient within the organization.
- `DELETE /NVIDataReference` with `pseudonym`, `oprfKey`, and `careContext` deletes a specific registration.

Example CURL request:

```curl
curl -X 'DELETE' \
  'https://nvi/NVIDataReference?source=90000001&careContext=LaboratoryTestResult&' \
  'pseudonym=<<encrypted-pseudonym-jwe>>&oprfKey=<<base64-encoded-oprf-key>>' \
  -H 'accept: application/fhir+json' \
  -H 'Authorization: Bearer <<access_token>>'
```

Example response:

``` HTTP
HTTP/1.1 204 No Content
```

### Get NVIDataReference by ID

Retrieves a specific `NVIDataReference` resource by ID.

| | |
| --- | --- |
| Path | /NVIDataReference/{id} |
| Type | GET |
| Query Parameters | None |

Example CURL request:

```curl
curl -X 'GET' \
  'https://nvi/NVIDataReference/12345' \
  -H 'accept: application/fhir+json' \
  -H 'Authorization: Bearer <<access_token>>'
```

Example response:

``` HTTP
Content-Type: application/fhir+json
```

```json
{
  "resourceType": "NVIDataReference",
  "id": "12345",
  "meta": {
    "versionId": "1",
    "lastUpdated": "2024-12-08T14:40:00Z"
  },
  "source": {
    "system": "https://example.org/fhir/NamingSystem/source",
    "value": "90000001"
  },
  "sourceType": {
    "coding": [
      {
        "system": "https://example.org/fhir/CodeSystem/source-type",
        "code": "laboratorium",
        "display": "Laboratorium"
      }
    ]
  },
  "careContext": {
    "coding": [
      {
        "system": "https://example.org/fhir/CodeSystem/care-context",
        "code": "LaboratoryTestResult",
        "display": "Laboratorium uitslag"
      }
    ]
  }
}
```

### Delete NVIDataReference by ID

Deletes a specific `NVIDataReference` resource by ID.

| | |
| --- | --- |
| Path | /NVIDataReference/{id} |
| Type | DELETE |
| Query Parameters | None |

Example CURL request:

```curl
curl -X 'DELETE' \
  'https://nvi/NVIDataReference/12345' \
  -H 'accept: application/fhir+json' \
  -H 'Authorization: Bearer <<access_token>>'
```

Example response:

``` HTTP
HTTP/1.1 204 No Content
```
