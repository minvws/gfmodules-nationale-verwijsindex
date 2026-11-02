import logging

import gfmodules.logging as gflog
from gfmodules.logging.testing import assert_event_emitted, assert_fields_absent, capture_records

from app.logging.context import bind_auth_claims
from app.logging.events import Log
from app.models.auth.context import AuthContext, AuthenticationClaims
from app.models.auth.data import AuthorizationScope
from app.models.ura import UraNumber

_logger = logging.getLogger("app.test_context")

_OIN = "00000001123456700000"


def _auth(oin: str | None) -> AuthContext:
    return AuthContext(
        claims=AuthenticationClaims(ura_number=UraNumber("123"), organization_name="Some Org", oin=oin),
        scope=[AuthorizationScope.CREATE],
        audience="nvi.service",
    )


def test_binds_the_organizations_of_the_caller() -> None:
    with capture_records(_logger.name) as records, bind_auth_claims(_auth(_OIN)):
        gflog.emit(_logger, Log.IDEMPOTENT_REGISTRATION, "registered")

    assert_event_emitted(
        records,
        Log.IDEMPOTENT_REGISTRATION,
        organization_name="Some Org",
        organization_identifier="00000123",
        acting_organization_identifier=_OIN,
    )


def test_binds_no_acting_organization_when_the_caller_has_no_oin() -> None:
    with capture_records(_logger.name) as records, bind_auth_claims(_auth(None)):
        gflog.emit(_logger, Log.IDEMPOTENT_REGISTRATION, "registered")

    assert_fields_absent([entry.message for entry in records], "acting_organization_identifier")


def test_binds_nothing_without_an_auth_context() -> None:
    with capture_records(_logger.name) as records, bind_auth_claims(None):
        gflog.emit(_logger, Log.IDEMPOTENT_REGISTRATION, "registered")

    assert_fields_absent(
        [entry.message for entry in records],
        "organization_name",
        "organization_identifier",
        "acting_organization_identifier",
    )
