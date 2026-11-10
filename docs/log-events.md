# Log events

<!-- markdownlint-disable MD013 -->

Generated from `app.logging.events:Log` by `gfmodules.logging.event_overview`.
Do not edit by hand.

Each stream lists the events that reach it and the fields they carry there besides the context fields.
*any* means the event has no allow-list, so every field it is logged with reaches the stream.
*none* means the event carries only the context fields there.

## Context fields

Every event carries these on every stream, whenever the request context holds a value for them.

- `request_id`
- `ip`
- `user_agent`
- `client_trace_id`
- `correlation_id`
- `endpoint`
- `method`
- `scope`

The request context also holds these, but an event carries them only on the streams whose fields name them.

- `organization_name`
- `organization_identifier`
- `acting_organization_identifier`
- `acting_organization_name`

## Stream `public_inspect`

| Event | Id | Level | Fields |
| --- | --- | --- | --- |
| `REGISTERED_REFERRAL` | 900400 | INFO | `organization_name`, `organization_identifier`, `pseudonym_hash` |
| `REFERRAL_SEARCHED_ON_ID` | 900402 | INFO | `organization_name`, `organization_identifier`, `pseudonym_hash` |
| `REFERRAL_DELETED` | 900500 | INFO | `organization_name`, `organization_identifier`, `pseudonym_hash` |
| `ALL_PATIENT_REFERRALS_DELETED` | 900501 | WARNING | `organization_name`, `organization_identifier`, `pseudonym_hash`, `deleted_count` |
| `ALL_ORGANIZATION_REFERRALS_DELETED` | 900503 | CRITICAL | `organization_name`, `organization_identifier`, `deleted_count` |
| `LOCALIZATION_SUCCESS` | 900600 | INFO | `organization_name`, `organization_identifier`, `pseudonym_hash` |

## Stream `app`

| Event | Id | Level | Fields |
| --- | --- | --- | --- |
| `SYS_APP_STARTED` | 100601 | INFO | `version`, `config_path`, `crypto_service_api_enabled` |
| `SYS_APP_STOPPED` | 100602 | INFO | `shutdown_reason`, `last_exception_type` |
| `SYS_APP_CRASHED` | 100602 | CRITICAL | `shutdown_reason`, `last_exception_type` |
| `SYS_UNHANDLED_EXCEPTION` | 100604 | ERROR | `exception_type`, `endpoint`, `method` |
| `SYS_MISSING_CORRELATION_ID` | 100628 | ERROR | `endpoint`, `method` |
| `HEALTH_UNHEALTHY` | 100600 | ERROR | `component`, `status`, `error_detail` |
| `DB_CONNECTION_FAILED` | 100603 | ERROR | `error_type`, `retry_attempt`, `backoff_seconds` |
| `DB_SCHEMA_ERROR` | 100605 | ERROR | `exception_type`, `table`, `column`, `value_length`, `column_limit` |
| `REGISTERED_REFERRAL` | 900400 | INFO | `organization_identifier`, `acting_organization_identifier`, `acting_organization_name` |
| `IDEMPOTENT_REGISTRATION` | 900401 | INFO | `organization_identifier`, `acting_organization_identifier`, `acting_organization_name` |
| `REFERRAL_SEARCHED_ON_ID` | 900402 | INFO | `organization_identifier`, `acting_organization_identifier`, `acting_organization_name` |
| `REFERRALS_QUERIED` | 900403 | INFO | `organization_identifier`, `acting_organization_identifier`, `acting_organization_name`, `result_count` |
| `REFERRAL_REGISTRATION_FAILED` | 900404 | WARNING | `organization_identifier`, `acting_organization_identifier`, `acting_organization_name`, `http_status`, `error_reason` |
| `REFERRAL_ACCESS_DENIED` | 900405 | WARNING | `organization_identifier`, `acting_organization_identifier`, `acting_organization_name`, `resource_organization_identifier` |
| `REFERRAL_DELETED` | 900500 | INFO | `organization_identifier`, `acting_organization_identifier`, `acting_organization_name` |
| `ALL_PATIENT_REFERRALS_DELETED` | 900501 | WARNING | `organization_identifier`, `acting_organization_identifier`, `acting_organization_name`, `deleted_count` |
| `ALL_ORGANIZATION_REFERRALS_DELETED` | 900503 | CRITICAL | `organization_identifier`, `acting_organization_identifier`, `acting_organization_name`, `deleted_count` |
| `LOCALIZATION_SUCCESS` | 900600 | INFO | `organization_identifier`, `acting_organization_identifier`, `acting_organization_name`, `pseudonym_hash` |
| `LOCALIZATION_FAILED` | 900601 | WARNING | `organization_identifier`, `acting_organization_identifier`, `acting_organization_name`, `error_reason`, `http_status` |
| `LOCALIZATION_ERROR` | 900601 | ERROR | `organization_identifier`, `acting_organization_identifier`, `acting_organization_name`, `error_reason`, `http_status` |
| `LOCALIZATION_NO_MATCH` | 900602 | INFO | `organization_identifier`, `acting_organization_identifier`, `acting_organization_name`, `result_count` |
| `ACCESS_REQUEST` | 100 | INFO | `endpoint`, `method`, `status_code`, `status_code_missing`, `duration_ms`, `body`, `body_truncated` |

## Stream `siem`

| Event | Id | Level | Fields |
| --- | --- | --- | --- |
| `SYS_APP_STOPPED` | 100602 | INFO | `shutdown_reason` |
| `SYS_APP_CRASHED` | 100602 | CRITICAL | `shutdown_reason` |
| `SYS_UNHANDLED_EXCEPTION` | 100604 | ERROR | `exception_type`, `endpoint`, `method` |
| `HEALTH_UNHEALTHY` | 100600 | ERROR | `component`, `status` |
| `DB_CONNECTION_FAILED` | 100603 | ERROR | `error_type` |
| `REFERRAL_REGISTRATION_FAILED` | 900404 | WARNING | `organization_identifier`, `acting_organization_identifier`, `acting_organization_name`, `http_status`, `error_reason` |
| `REFERRAL_ACCESS_DENIED` | 900405 | WARNING | `organization_identifier`, `acting_organization_identifier`, `acting_organization_name`, `resource_organization_identifier` |
| `ALL_PATIENT_REFERRALS_DELETED` | 900501 | WARNING | `organization_identifier`, `acting_organization_identifier`, `acting_organization_name`, `deleted_count` |
| `ALL_ORGANIZATION_REFERRALS_DELETED` | 900503 | CRITICAL | `organization_identifier`, `acting_organization_identifier`, `acting_organization_name`, `deleted_count` |
| `LOCALIZATION_SUCCESS` | 900600 | INFO | `organization_identifier`, `acting_organization_identifier`, `acting_organization_name`, `result_count` |
| `LOCALIZATION_FAILED` | 900601 | WARNING | `organization_identifier`, `acting_organization_identifier`, `acting_organization_name`, `error_reason`, `http_status` |
| `LOCALIZATION_ERROR` | 900601 | ERROR | `organization_identifier`, `acting_organization_identifier`, `acting_organization_name`, `error_reason`, `http_status` |
