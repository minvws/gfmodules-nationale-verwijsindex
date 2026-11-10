import logging

import gfmodules.logging as gflog
from gfmodules.logging.testing import assert_event_emitted, assert_fields_absent, capture_records

from app.logging.context import set_auth_claims
from app.logging.events import Log
from app.models.auth.context import AuthContext, AuthenticationClaims
from app.models.auth.data import AuthorizationScope
from app.models.ura import UraNumber

_logger = logging.getLogger("app.test_context")

_OIN = "00000001123456700000"
_ACTING_ORGANIZATION_NAME = "client.example.nl"


_AUTH = AuthContext(
    claims=AuthenticationClaims(
        ura_number=UraNumber("123"),
        organization_name="Some Org",
        oin=_OIN,
        acting_organization_name=_ACTING_ORGANIZATION_NAME,
    ),
    scope=[AuthorizationScope.CREATE],
    audience="nvi.service",
)


def test_sets_the_organizations_of_the_caller() -> None:
    with capture_records(_logger.name) as records, gflog.bind_context({}):
        set_auth_claims(_AUTH)
        gflog.emit(_logger, Log.IDEMPOTENT_REGISTRATION, "registered")

    assert_event_emitted(
        records,
        Log.IDEMPOTENT_REGISTRATION,
        organization_name="Some Org",
        organization_identifier="00000123",
        acting_organization_identifier=_OIN,
        acting_organization_name=_ACTING_ORGANIZATION_NAME,
    )


def test_sets_nothing_without_an_auth_context() -> None:
    with capture_records(_logger.name) as records, gflog.bind_context({}):
        set_auth_claims(None)
        gflog.emit(_logger, Log.IDEMPOTENT_REGISTRATION, "registered")

    assert_fields_absent(
        [entry.message for entry in records],
        "organization_name",
        "organization_identifier",
        "acting_organization_identifier",
        "acting_organization_name",
    )
