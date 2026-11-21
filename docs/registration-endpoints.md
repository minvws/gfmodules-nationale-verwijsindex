# NVI Registration Endpoints Documentation

**Purpose:** This document provides maintainers with a comprehensive overview of the
Nationale Verwijsindex (NVI) API endpoints related to registration management,
localization, and data discovery.

**Note:** This documentation focuses on the core registration and data discovery
functionality.

---

## Authentication

All authenticated requests require an OAuth 2.0 bearer token. Based on this token, the following trusted headers are
set by the authentication middleware:

- **URA Number** (`x-gf-sub`): The healthcare provider's unique identifier (e.g., `12345678`)
- **source_id** (`x-gf-source-id`): The application identifier that scopes the organization's data access
- **Scope** (`x-gf-scope`): OAuth scopes (e.g., `nvi:create`, `nvi:read`, `nvi:delete`, `nvi:localize`) that determine
which operations are permitted

These header values are then used by the application to:

- Validate the user's scope permissions
- Scope data access to the authenticated provider's organization and specific application instance (via source_id)
- Enforce data isolation between different healthcare providers

---

## FHIR Bundle API

The FHIR Bundle API (`POST /fhir`) supports transaction operations for registration management. The localization
functionality is not supported in a bundle.

---

## Endpoint Matrix

| **Functionality** | **FHIR List Endpoint** | **Plain Endpoints** | **Required Scope** | **Query Scope** | **Source ID Required** | **Supported in FHIR Bundle?** |
| ----------------- | ---------------------- | ------------------- | ----------------- | --------------- | ------------------- | ------------------------------- |
| **Create Registration** | `POST /fhir/List` | `POST /registrations` | `nvi:create` | Own URA | Yes | ✅ Yes |
| **Get Registration by ID** | `GET /fhir/List/{id}` | N/A | `nvi:read` | Own URA | Yes | ✅ Yes |
| **Query Own Registrations** | `GET /fhir/List?source:identifier={ura}&subject:identifier={pseudo}` | `GET /registrations?pseudonym={pseudo}&oprfKey={key}` | `nvi:read` | Own URA | Yes | ❌ No |
| **Delete Registration by ID** | `DELETE /fhir/List/{id}` | N/A | `nvi:delete` | Own URA | Yes | ✅ Yes |
| **Delete Registrations** | `DELETE /fhir/List?source:identifier={ura}&subject:identifier={pseudo}` | `DELETE /registrations?pseudonym={pseudo}&oprfKey={key}` | `nvi:delete` | Own URA | Yes | ✅ Yes |
| **Delete Registration** | `DELETE /fhir/List?source:identifier={ura}&subject:identifier={pseudo}` | `DELETE /registrations?pseudonym={pseudo}&oprfKey={key}` | `nvi:delete` | Own URA | Yes | ✅ Yes |
| **Find All Providers for Patient** | `GET /fhir/List?subject:identifier={pseudo}` | `POST /localize` | `nvi:localize` | **All URAs** | No | ❌ No |

---

## Functional Summary

### Registration Creation

- **Purpose:** Record that a healthcare provider has data for a specific patient

- **FHIR List:** `POST /fhir/List` - Uses FHIR List resource format with extensions
for URA and pseudonym

- **Plain API:** `POST /registrations` - Uses custom JSON format with pseudonym and
OPRF key

- **Scope:** `nvi:create`

- **Source ID Required:** Yes

- **Idempotency:** Duplicate registrations return existing resource (HTTP 200)
instead of creating duplicates

- **Authorization:** Only the authenticated provider can create registrations for
their own URA

### Registration Retrieval by ID

- **Purpose:** Retrieve a specific registration by its unique identifier

- **FHIR List:** `GET /fhir/List/{id}` - Returns FHIR List resource

- **Plain API:** Not available

- **Scope:** `nvi:read`

- **Source ID Required:** Yes

- **Authorization:** Only returns if the authenticated URA matches the registration's
source

### Registration Deletion by ID

- **Purpose:** Delete a specific registration by its unique identifier

- **FHIR List:** `DELETE /fhir/List/{id}`

- **Plain API:** Not available

- **Scope:** `nvi:delete`

- **Source ID Required:** Yes

- **Authorization:** Only deletes if the authenticated URA matches the registration's
source

- **Affected registrations:** Exactly one registration (due to unique constraint on
`(ura_number, pseudonym, source)`)

### Delete Registration

- **Purpose:** Delete registration for a specific patient within the authenticated provider's own organization and
source identifier

- **FHIR List:** `DELETE /fhir/List?source:identifier={ura}&subject:identifier={pseudo}`

- **Plain API:** `DELETE /registrations?pseudonym={pseudo}&oprfKey={key}`

- **Scope:** `nvi:delete`

- **Source ID Required:** Yes

- **Query Scope:** Deletes only registrations from the authenticated URA and source identifier

- **Source:** Extracted from OAuth token claims (not from query parameters)

- **Affected registrations:** Exactly one registration (due to unique constraint on
`(ura_number, pseudonym, source)`)

- **Note:** Referrals are identified by patient pseudonym, provider URA, and source
identifier only. The unique constraint ensures only one registration can exist for
each combination.

### Query Own Registrations

- **Purpose:** Retrieve all registrations created by the authenticated provider for a
specific patient

- **FHIR List:** `GET /fhir/List?source:identifier={ura}&subject:identifier={pseudo}`

- **Plain API:** `GET /registrations?pseudonym={pseudo}&oprfKey={key}`

- **Note:** Referrals are identified by patient pseudonym, provider URA, and source
identifier.

- **Scope:** `nvi:read`

- **Source ID Required:** Yes

- **Query Scope:** Returns only registrations from the authenticated URA

- **Pagination:**
  - **FHIR List:** Supports pagination via `_count` (default: 10, max: 100) and
`_offset` parameters
  - **Plain API:** Returns all matching registrations in a single response (no
pagination)

### Cross-Provider Discovery (Localization)

- **Purpose:** Find all healthcare providers that have data for a specific patient,
regardless of which provider is querying

- **FHIR List:** `GET /fhir/List?subject:identifier={pseudo}` - Note: No source parameter

- **Plain API:** `POST /localize` - Uses FHIR Parameters resource in request body

- **Scope:** `nvi:localize`

- **Source ID Required:** No

- **Query Scope:** Returns registrations from **all providers** (not just the
authenticated URA)

- **Use Case:** Enable healthcare providers to discover external data sources for
continuity of care

- **Key Difference:** This is the only functionality that returns data across all
providers

- **Pagination:**
  - **FHIR List:** Supports pagination via `_count` (default: 10, max: 100) and
`_offset` parameters
  - **Plain API:** Not applicable (single operation, no pagination)
