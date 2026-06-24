import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from app.logging.filters import LoggingStreams

_APP = LoggingStreams.APP
_SIEM = LoggingStreams.SIEM


@dataclass(frozen=True)
class NVIEvent:
    event_id: str
    level: int
    streams: tuple[LoggingStreams, ...]
    # Per-stream allow-list of field names. APP == "stroom 2", SIEM == "stroom 3".
    # When empty, no per-field routing is applied and every field is sent to all
    # streams in ``streams`` (used by the System / Health events).
    fields: Mapping[LoggingStreams, tuple[str, ...]] = field(default_factory=dict)


class Log:
    # System / Health (NVI-SYS / NVI-HEALTH)
    SYS_APP_STARTED = NVIEvent("100601", logging.INFO, (_APP,))
    SYS_APP_STOPPED = NVIEvent("100602", logging.INFO, (_APP, _SIEM))
    SYS_APP_CRASHED = NVIEvent("100602", logging.CRITICAL, (_APP, _SIEM))
    SYS_UNHANDLED_EXCEPTION = NVIEvent("100604", logging.ERROR, (_APP,))
    HEALTH_UNHEALTHY = NVIEvent("100600", logging.ERROR, (_APP, _SIEM))

    ACCESS_REQUEST = NVIEvent(  # NVI-AUTH-101
        "094500",
        logging.INFO,
        (_APP,),
        {_APP: ("endpoint", "method")},
    )

    REGISTERED_REFERRAL = NVIEvent(  # NVI-REF-001
        "900400",
        logging.INFO,
        (_APP, _SIEM),
        {
            _APP: ("organization", "ura_number", "pseudonym_hash"),
            _SIEM: ("ura_number",),
        },
    )
    IDEMPOTENT_REGISTRATION = NVIEvent(  # NVI-REF-002
        "900401",
        logging.INFO,
        (_SIEM,),
        {_SIEM: ("ura_number",)},
    )
    REFERRAL_SEARCHED_ON_ID = NVIEvent(  # NVI-REF-003
        "900402",
        logging.INFO,
        (_APP, _SIEM),
        {
            _APP: ("organization", "ura_number", "pseudonym_hash"),
            _SIEM: ("ura_number",),
        },
    )
    REFERRALS_QUERIED = NVIEvent(  # NVI-REF-004
        "900403",
        logging.INFO,
        (_SIEM,),
        {
            _SIEM: ("ura_number", "org_type_filter", "result_count"),
        },
    )
    REFERRAL_REGISTRATION_FAILED = NVIEvent(  # NVI-REF-005
        "900404",
        logging.WARNING,
        (_SIEM,),
        {_SIEM: ("ura_number", "endpoint", "http_status", "error_reason")},
    )
    REFERRAL_ACCESS_DENIED = NVIEvent(  # NVI-REF-006
        "900405",
        logging.WARNING,
        (_SIEM,),
        {_SIEM: ("ura_number", "resource_ura", "endpoint")},
    )

    REFERRAL_DELETED = NVIEvent(  # NVI-DEL-001
        "900500",
        logging.INFO,
        (_APP, _SIEM),
        {
            _APP: ("organization", "ura_number", "pseudonym_hash"),
            _SIEM: ("ura_number",),
        },
    )
    ALL_PATIENT_REFERRALS_DELETED = NVIEvent(  # NVI-DEL-002
        "900501",
        logging.WARNING,
        (_APP, _SIEM),
        {
            _APP: ("organization", "ura_number", "pseudonym_hash", "deleted_count"),
            _SIEM: ("ura_number", "deleted_count"),
        },
    )
    ALL_URA_REFERRALS_DELETED = NVIEvent(  # NVI-DEL-004
        "900503",
        logging.CRITICAL,
        (_APP, _SIEM),
        {
            _APP: ("organization", "ura_number", "deleted_count"),
            _SIEM: ("ura_number", "deleted_count"),
        },
    )

    LOCALIZATION_SUCCESS = NVIEvent(  # NVI-LOC-001
        "900600",
        logging.INFO,
        (_APP, _SIEM),
        {
            _APP: ("organizations", "ura_number", "pseudonym_hash"),
            _SIEM: ("ura_number", "org_type_filter", "result_count"),
        },
    )
    LOCALIZATION_FAILED = NVIEvent(  # NVI-LOC-002
        "900601",
        logging.WARNING,
        (_SIEM,),
        {_SIEM: ("ura_number", "error_reason", "http_status")},
    )
    LOCALIZATION_ERROR = NVIEvent(  # NVI-LOC-002
        "900601",
        logging.ERROR,
        (_SIEM,),
        {_SIEM: ("ura_number", "error_reason", "http_status")},
    )
    LOCALIZATION_NO_MATCH = NVIEvent(  # NVI-LOC-003
        "900602",
        logging.INFO,
        (_SIEM,),
        {_SIEM: ("ura_number", "org_type_filter", "result_count")},
    )

    @staticmethod
    def event(
        logger: logging.Logger,
        event: NVIEvent,
        message: str,
        *,
        exc_info: Any = None,
        **fields: Any,
    ) -> None:
        extra: dict[str, Any] = {
            "event_id": event.event_id,
            "stream": list(event.streams),
        }
        if event.fields:
            extra["field_streams"] = event.fields
        extra.update(fields)
        logger.log(event.level, message, extra=extra, exc_info=exc_info)
