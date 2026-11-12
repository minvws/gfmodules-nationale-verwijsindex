import logging

from gfmodules.logging import DefaultEventCatalogue, LogEvent, LoggingStreams

from app.logging.context import CLAIM_FIELDS

_APP = LoggingStreams.APP
_SIEM = LoggingStreams.SIEM
_PUB = LoggingStreams.PUBLIC_INSPECT

_CALLER = ("organization_identifier", "acting_organization_identifier", "acting_organization_name")

_Base = DefaultEventCatalogue


class Log(_Base):
    context_fields = CLAIM_FIELDS

    SYS_APP_STARTED = _Base.SYS_APP_STARTED.replace(  # NVI-SYS-001
        event_id="100601",
        fields={_APP: ("version", "config_path", "crypto_service_api_enabled")},
    )
    SYS_APP_STOPPED = _Base.SYS_APP_STOPPED.with_id("100602")  # NVI-SYS-002
    SYS_APP_CRASHED = _Base.SYS_APP_CRASHED.with_id("100602")  # NVI-SYS-002
    SYS_UNHANDLED_EXCEPTION = _Base.SYS_UNHANDLED_EXCEPTION.with_id("100604")  # NVI-SYS-004
    SYS_MISSING_CORRELATION_ID = _Base.SYS_MISSING_CORRELATION_ID.with_id("100606")  # NVI-SYS-006

    HEALTH_UNHEALTHY = LogEvent(  # NVI-HEALTH-001
        "100600",
        logging.ERROR,
        (_APP, _SIEM),
        {_APP: ("component", "status", "error_detail"), _SIEM: ("component", "status")},
    )

    DB_CONNECTION_FAILED = LogEvent(  # NVI-SYS-003
        "100603",
        logging.ERROR,
        (_APP, _SIEM),
        {_APP: ("error_type", "retry_attempt", "backoff_seconds"), _SIEM: ("error_type",)},
    )
    DB_SCHEMA_ERROR = LogEvent(  # NVI-SYS-005
        "100605",
        logging.ERROR,
        (_APP,),
        {
            _APP: ("exception_type", "table", "column", "value_length", "column_limit"),
        },
    )

    REGISTERED_REFERRAL = LogEvent(  # NVI-REF-001
        "900400",
        logging.INFO,
        (_PUB, _APP),
        {
            _PUB: ("organization_name", "organization_identifier", "pseudonym_hash"),
            _APP: _CALLER,
        },
    )
    IDEMPOTENT_REGISTRATION = LogEvent(  # NVI-REF-002
        "900401",
        logging.INFO,
        (_APP,),
        {_APP: _CALLER},
    )
    REFERRAL_SEARCHED_ON_ID = LogEvent(  # NVI-REF-003
        "900402",
        logging.INFO,
        (_PUB, _APP),
        {
            _PUB: ("organization_name", "organization_identifier", "pseudonym_hash"),
            _APP: _CALLER,
        },
    )
    REFERRALS_QUERIED = LogEvent(  # NVI-REF-004
        "900403",
        logging.INFO,
        (_APP,),
        {
            _APP: (*_CALLER, "result_count"),
        },
    )
    REFERRAL_REGISTRATION_FAILED = LogEvent(  # NVI-REF-005
        "900404",
        logging.WARNING,
        (_APP, _SIEM),
        {
            _APP: (*_CALLER, "http_status", "error_reason"),
            _SIEM: (*_CALLER, "http_status", "error_reason"),
        },
    )
    REFERRAL_REGISTRATION_ERROR = REFERRAL_REGISTRATION_FAILED.replace(level=logging.ERROR)
    REFERRAL_ACCESS_DENIED = LogEvent(  # NVI-REF-006
        "900405",
        logging.WARNING,
        (_APP, _SIEM),
        {
            _APP: (*_CALLER, "resource_ura"),
            _SIEM: (*_CALLER, "resource_ura"),
        },
    )

    REFERRAL_DELETED = LogEvent(  # NVI-DEL-001
        "900500",
        logging.INFO,
        (_PUB, _APP),
        {
            _PUB: ("organization_name", "organization_identifier", "pseudonym_hash"),
            _APP: _CALLER,
        },
    )
    ALL_PATIENT_REFERRALS_DELETED = LogEvent(  # NVI-DEL-002
        "900501",
        logging.WARNING,
        (_PUB, _APP, _SIEM),
        {
            _PUB: ("organization_name", "organization_identifier", "pseudonym_hash", "deleted_count"),
            _APP: (*_CALLER, "deleted_count"),
            _SIEM: (*_CALLER, "deleted_count"),
        },
    )
    ALL_URA_REFERRALS_DELETED = LogEvent(  # NVI-DEL-004
        "900503",
        logging.CRITICAL,
        (_PUB, _APP, _SIEM),
        {
            _PUB: ("organization_name", "organization_identifier", "deleted_count"),
            _APP: (*_CALLER, "deleted_count"),
            _SIEM: (*_CALLER, "deleted_count"),
        },
    )

    LOCALIZATION_SUCCESS = LogEvent(  # NVI-LOC-001
        "900600",
        logging.INFO,
        (_PUB, _APP, _SIEM),
        {
            _PUB: ("organization_name", "organization_identifier", "pseudonym_hash"),
            _APP: (*_CALLER, "pseudonym_hash"),
            _SIEM: (*_CALLER, "result_count"),
        },
    )
    LOCALIZATION_FAILED = LogEvent(  # NVI-LOC-002
        "900601",
        logging.WARNING,
        (_APP, _SIEM),
        {
            _APP: (*_CALLER, "error_reason", "http_status"),
            _SIEM: (*_CALLER, "error_reason", "http_status"),
        },
    )
    LOCALIZATION_ERROR = LogEvent(  # NVI-LOC-002
        "900601",
        logging.ERROR,
        (_APP, _SIEM),
        {
            _APP: (*_CALLER, "error_reason", "http_status"),
            _SIEM: (*_CALLER, "error_reason", "http_status"),
        },
    )
    LOCALIZATION_NO_MATCH = LogEvent(  # NVI-LOC-003
        "900602",
        logging.INFO,
        (_APP,),
        {_APP: (*_CALLER, "result_count")},
    )
