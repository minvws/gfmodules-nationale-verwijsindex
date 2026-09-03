import logging

from gfmodules.logging import DefaultEventCatalogue, LogEvent, LoggingStreams

_APP = LoggingStreams.APP
_SIEM = LoggingStreams.SIEM
_PUB = LoggingStreams.PUBLIC_INSPECT

_Base = DefaultEventCatalogue


class Log(_Base):
    SYS_APP_STARTED = _Base.SYS_APP_STARTED.replace(  # NVI-SYS-001
        event_id="100601",
        fields={_APP: ("version", "config_path", "crypto_service_api_enabled")},
    )
    SYS_APP_STOPPED = _Base.SYS_APP_STOPPED.with_id("100602")  # NVI-SYS-002
    SYS_APP_CRASHED = _Base.SYS_APP_CRASHED.with_id("100602")  # NVI-SYS-002
    SYS_UNHANDLED_EXCEPTION = _Base.SYS_UNHANDLED_EXCEPTION.with_id("100604")  # NVI-SYS-004
    SYS_MISSING_CORRELATION_ID = _Base.SYS_MISSING_CORRELATION_ID.with_id("100606")  # NVI-SYS-006
    ACCESS_REQUEST = _Base.ACCESS_REQUEST.with_id("094500")  # NVI-AUTH-101

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
        {_PUB: ("organization", "ura_number", "pseudonym_hash"), _APP: ("ura_number",)},
    )
    IDEMPOTENT_REGISTRATION = LogEvent(  # NVI-REF-002
        "900401",
        logging.INFO,
        (_APP,),
        {_APP: ("ura_number",)},
    )
    REFERRAL_SEARCHED_ON_ID = LogEvent(  # NVI-REF-003
        "900402",
        logging.INFO,
        (_PUB, _APP),
        {_PUB: ("organization", "ura_number", "pseudonym_hash"), _APP: ("ura_number",)},
    )
    REFERRALS_QUERIED = LogEvent(  # NVI-REF-004
        "900403",
        logging.INFO,
        (_APP,),
        {
            _APP: ("ura_number", "result_count"),
        },
    )
    REFERRAL_REGISTRATION_FAILED = LogEvent(  # NVI-REF-005
        "900404",
        logging.WARNING,
        (_APP, _SIEM),
        {
            _APP: ("ura_number", "endpoint", "http_status", "error_reason"),
            _SIEM: ("ura_number", "http_status", "error_reason"),
        },
    )
    REFERRAL_ACCESS_DENIED = LogEvent(  # NVI-REF-006
        "900405",
        logging.WARNING,
        (_APP, _SIEM),
        {_APP: ("ura_number", "resource_ura", "endpoint"), _SIEM: ("ura_number", "resource_ura")},
    )

    REFERRAL_DELETED = LogEvent(  # NVI-DEL-001
        "900500",
        logging.INFO,
        (_PUB, _APP),
        {_PUB: ("organization", "ura_number", "pseudonym_hash"), _APP: ("ura_number",)},
    )
    ALL_PATIENT_REFERRALS_DELETED = LogEvent(  # NVI-DEL-002
        "900501",
        logging.WARNING,
        (_PUB, _APP, _SIEM),
        {
            _PUB: ("organization", "ura_number", "pseudonym_hash", "deleted_count"),
            _APP: ("ura_number", "deleted_count"),
            _SIEM: ("ura_number", "deleted_count"),
        },
    )
    ALL_URA_REFERRALS_DELETED = LogEvent(  # NVI-DEL-004
        "900503",
        logging.CRITICAL,
        (_PUB, _APP, _SIEM),
        {
            _PUB: ("organization", "ura_number", "deleted_count"),
            _APP: ("ura_number", "deleted_count"),
            _SIEM: ("ura_number", "deleted_count"),
        },
    )

    LOCALIZATION_SUCCESS = LogEvent(  # NVI-LOC-001
        "900600",
        logging.INFO,
        (_PUB, _APP, _SIEM),
        {
            _PUB: ("organization", "ura_number", "pseudonym_hash"),
            _APP: ("ura_number", "pseudonym_hash"),
            _SIEM: ("ura_number", "result_count"),
        },
    )
    LOCALIZATION_FAILED = LogEvent(  # NVI-LOC-002
        "900601",
        logging.WARNING,
        (_APP, _SIEM),
        {_APP: ("ura_number", "error_reason", "http_status"), _SIEM: ("ura_number", "error_reason", "http_status")},
    )
    LOCALIZATION_ERROR = LogEvent(  # NVI-LOC-002
        "900601",
        logging.ERROR,
        (_APP, _SIEM),
        {_APP: ("ura_number", "error_reason", "http_status"), _SIEM: ("ura_number", "error_reason", "http_status")},
    )
    LOCALIZATION_NO_MATCH = LogEvent(  # NVI-LOC-003
        "900602",
        logging.INFO,
        (_APP,),
        {_APP: ("ura_number", "result_count")},
    )
