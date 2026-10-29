import logging

import gfmodules.logging as gflog
from gfmodules.logging.testing import assert_event_emitted, assert_fields_absent, capture_records

from app.logging.context import bind_auth_claims
from app.logging.events import Log
from app.models.auth.context import AuthContext, AuthenticationClaims
from app.models.auth.data import AuthorizationScope
from app.models.ura import UraNumber

_logger = logging.getLogger("app.test_context")

_AUTH = AuthContext(
    claims=AuthenticationClaims(ura_number=UraNumber("123"), organization_name="Some Org"),
    scope=[AuthorizationScope.CREATE],
    audience="nvi.service",
)


def test_binds_the_organization_and_ura_number_of_the_caller() -> None:
    with capture_records(_logger.name) as records, bind_auth_claims(_AUTH):
        gflog.emit(_logger, Log.IDEMPOTENT_REGISTRATION, "registered")

    assert_event_emitted(records, Log.IDEMPOTENT_REGISTRATION, organization="Some Org", ura_number="00000123")


def test_binds_nothing_without_an_auth_context() -> None:
    with capture_records(_logger.name) as records, bind_auth_claims(None):
        gflog.emit(_logger, Log.IDEMPOTENT_REGISTRATION, "registered")

    assert_fields_absent([entry.message for entry in records], "organization", "ura_number")
