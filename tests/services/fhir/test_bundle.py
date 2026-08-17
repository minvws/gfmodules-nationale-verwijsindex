import logging
from typing import Any, Literal
from uuid import uuid4

import pytest

from app.debug.crypto_service_api_client_mock import CryptoServiceApiClientMock
from app.logging.events import Log
from app.models.auth.context import AuthContext, AuthenticationClaims
from app.models.auth.data import AuthorizationScope
from app.models.fhir.bundle import Bundle, BundleEntry, EntryRequest
from app.models.fhir.resources.localization_list.resource import LocalizationList
from app.models.fhir.resources.operation_outcome.resource import OperationOutcome
from app.models.ura import UraNumber
from app.services.fhir.bundle import BundleService
from app.services.fhir.localization_list import LocalizationListService
from app.services.key_info import KeyInfoService
from app.services.pseudonym_resolver import PseudonymResolver
from app.services.referral_service import ReferralService
from tests.conftest import make_list_resource

AUTH_URA = UraNumber("00000001")
TEST_SOURCE_ID = "SRC-001"

ALL_SCOPES = [
    AuthorizationScope.CREATE,
    AuthorizationScope.READ,
    AuthorizationScope.DELETE,
    AuthorizationScope.LOCALIZE,
]


def _process(bundle_service: BundleService, entry: BundleEntry[Any], index: int = 0) -> BundleEntry[Any]:
    """Every caller here holds every scope and the entries reach the service."""
    ctx = AuthContext(
        claims=AuthenticationClaims(
            ura_number=AUTH_URA,
            organization_name="Org",
            source_id=TEST_SOURCE_ID,
        ),
        scope=ALL_SCOPES,
        audience="nvi.service",
    )
    return bundle_service.process_entry(ctx=ctx, entry=entry, index=index)


@pytest.fixture()
def bundle_service(
    referral_service: ReferralService,
    key_info_service: KeyInfoService,
) -> BundleService:
    resolver = PseudonymResolver(crypto_client=CryptoServiceApiClientMock(), key_info_service=key_info_service)
    localization_service = LocalizationListService(referral_service=referral_service, pseudonym_resolver=resolver)
    return BundleService(localization_service)


def _entry(method: Literal["POST", "DELETE", "GET", "PUT"], url: str) -> BundleEntry[LocalizationList]:
    return BundleEntry(request=EntryRequest(method=method, url=url))


def test_post_returns_the_stored_resource(bundle_service: BundleService, key_info_service: KeyInfoService) -> None:
    key_info_service.add_one("nvi-label", "AES_CBC")
    entry: BundleEntry[LocalizationList] = BundleEntry(
        request=EntryRequest(method="POST", url="List"),
        resource=make_list_resource(ura=str(AUTH_URA)),
    )

    result = _process(bundle_service, entry, index=0)

    assert result.response is not None
    assert result.response.status == "200"
    assert result.resource is not None
    assert result.resource.id is not None


def test_get_by_missing_id_maps_not_found_to_404(bundle_service: BundleService) -> None:
    entry = _entry("GET", f"List/{uuid4()}")

    result = _process(bundle_service, entry, index=0)

    assert result.response is not None
    assert result.response.status == "404"


def test_delete_by_missing_id_maps_not_found_to_404(bundle_service: BundleService) -> None:
    entry = _entry("DELETE", f"List/{uuid4()}")

    result = _process(bundle_service, entry, index=0)

    assert result.response is not None
    assert result.response.status == "404"


def test_missing_request_returns_validation_response(bundle_service: BundleService) -> None:
    entry: BundleEntry[LocalizationList] = BundleEntry()

    result = _process(bundle_service, entry, index=0)

    assert result.response is not None
    assert result.response.status == "422"


def test_unsupported_method_returns_forbidden(bundle_service: BundleService) -> None:
    entry = _entry("PUT", "List")

    result = _process(bundle_service, entry, index=0)

    assert result.response is not None
    assert result.response.status == "403"


def test_unsupported_resource_in_url_returns_validation(bundle_service: BundleService) -> None:
    entry = _entry("GET", f"Patient/{uuid4()}")

    result = _process(bundle_service, entry, index=0)

    assert result.response is not None
    assert result.response.status == "422"


def test_post_without_resource_returns_validation(bundle_service: BundleService) -> None:
    entry = _entry("POST", "List")

    result = _process(bundle_service, entry, index=0)

    assert result.response is not None
    assert result.response.status == "422"


class TestUrlResolution:
    def test_malformed_url_returns_validation_response(self, bundle_service: BundleService) -> None:
        result = _process(bundle_service, _entry("GET", "http://["), index=0)

        assert result.response is not None
        assert result.response.status == "422"

    def test_url_with_both_id_and_params_is_rejected(self, bundle_service: BundleService) -> None:
        result = _process(bundle_service, _entry("GET", f"List/{uuid4()}?source:identifier=SRC-001"), index=0)

        assert result.response is not None
        assert result.response.status == "422"


class TestEntryValidation:
    def test_get_with_invalid_query_params_returns_validation_response(self, bundle_service: BundleService) -> None:
        result = _process(bundle_service, _entry("GET", "List?unsupported=1"), index=0)

        assert result.response is not None
        assert result.response.status == "422"

    def test_delete_with_invalid_query_params_returns_validation_response(self, bundle_service: BundleService) -> None:
        result = _process(bundle_service, _entry("DELETE", "List?unsupported=1"), index=0)

        assert result.response is not None
        assert result.response.status == "422"


class TestBundleStructure:
    def test_empty_bundle_is_invalid(self) -> None:
        assert BundleService.validate_localization_bundle_structure(Bundle(entry=[])) is False

    def test_bundle_with_entries_is_valid(self) -> None:
        assert BundleService.validate_localization_bundle_structure(Bundle(entry=[BundleEntry()])) is True


class TestEntryOutcomes:
    def test_get_query_returns_searchset_bundle(
        self, bundle_service: BundleService, key_info_service: KeyInfoService
    ) -> None:
        key_info_service.add_one("nvi-label", "AES_CBC")

        result = _process(bundle_service, _entry("GET", "List?source:identifier=SRC-001"), index=0)

        assert result.response is not None
        assert result.response.status == "200"
        assert result.resource is not None

    def test_delete_by_query_returns_service_status(
        self, bundle_service: BundleService, key_info_service: KeyInfoService
    ) -> None:
        key_info_service.add_one("nvi-label", "AES_CBC")
        post: BundleEntry[LocalizationList] = BundleEntry(
            request=EntryRequest(method="POST", url="List"),
            resource=make_list_resource(ura=str(AUTH_URA)),
        )
        _process(bundle_service, post, index=0)

        result = _process(bundle_service, _entry("DELETE", "List?source:identifier=SRC-001"), index=1)

        assert result.response is not None
        assert result.response.status == "201"

    def test_get_by_id_returns_resource(self, bundle_service: BundleService, key_info_service: KeyInfoService) -> None:
        key_info_service.add_one("nvi-label", "AES_CBC")
        post: BundleEntry[LocalizationList] = BundleEntry(
            request=EntryRequest(method="POST", url="List"),
            resource=make_list_resource(ura=str(AUTH_URA)),
        )
        created = _process(bundle_service, post, index=0)
        assert created.resource is not None

        result = _process(bundle_service, _entry("GET", f"List/{created.resource.id}"), index=1)

        assert result.response is not None
        assert result.response.status == "200"
        assert result.resource is not None
        assert result.resource.id == created.resource.id

    def test_delete_by_id_returns_service_status(
        self, bundle_service: BundleService, key_info_service: KeyInfoService
    ) -> None:
        key_info_service.add_one("nvi-label", "AES_CBC")
        post: BundleEntry[LocalizationList] = BundleEntry(
            request=EntryRequest(method="POST", url="List"),
            resource=make_list_resource(ura=str(AUTH_URA)),
        )
        created = _process(bundle_service, post, index=0)
        assert created.resource is not None

        result = _process(bundle_service, _entry("DELETE", f"List/{created.resource.id}"), index=1)

        assert result.response is not None
        assert result.response.status == "201"


class TestEntryFailureMapping:
    def test_post_for_another_ura_maps_to_403(
        self, bundle_service: BundleService, key_info_service: KeyInfoService
    ) -> None:
        key_info_service.add_one("nvi-label", "AES_CBC")
        entry: BundleEntry[LocalizationList] = BundleEntry(
            request=EntryRequest(method="POST", url="List"),
            resource=make_list_resource(ura="99999999"),
        )

        result = _process(bundle_service, entry, index=0)

        assert result.response is not None
        assert result.response.status == "403"

    def test_post_with_malformed_pseudonym_maps_to_422_and_logs(
        self,
        bundle_service: BundleService,
        key_info_service: KeyInfoService,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        key_info_service.add_one("nvi-label", "AES_CBC")
        entry: BundleEntry[LocalizationList] = BundleEntry(
            request=EntryRequest(method="POST", url="List"),
            resource=make_list_resource(ura=str(AUTH_URA), pseudonym="not-a-valid-token!!!"),
        )

        with caplog.at_level(logging.WARNING):
            result = _process(bundle_service, entry, index=0)

        assert result.response is not None
        assert result.response.status == "422"
        event_ids = [r.event_id for r in caplog.records if hasattr(r, "event_id")]
        assert Log.REFERRAL_REGISTRATION_FAILED.event_id in event_ids

    def test_query_with_malformed_pseudonym_maps_to_422_and_logs(
        self,
        bundle_service: BundleService,
        key_info_service: KeyInfoService,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        key_info_service.add_one("nvi-label", "AES_CBC")

        with caplog.at_level(logging.WARNING):
            result = _process(bundle_service, _entry("GET", "List?subject:identifier=not-a-valid-token!!!"), index=0)

        assert result.response is not None
        assert result.response.status == "422"
        event_ids = [r.event_id for r in caplog.records if hasattr(r, "event_id")]
        assert Log.LOCALIZATION_FAILED.event_id in event_ids

    def test_failure_without_a_failure_event_is_not_logged(
        self, bundle_service: BundleService, caplog: pytest.LogCaptureFixture
    ) -> None:
        # GET-by-id passes no failure_event, so a missing record produces an error entry
        # without an operational log line.
        with caplog.at_level(logging.WARNING):
            result = _process(bundle_service, _entry("GET", f"List/{uuid4()}"), index=0)

        assert result.response is not None
        assert result.response.status == "404"
        assert [r.event_id for r in caplog.records if hasattr(r, "event_id")] == []


def test_post_with_a_non_list_resource_returns_validation_response(
    bundle_service: BundleService, caplog: pytest.LogCaptureFixture
) -> None:
    entry: BundleEntry[Any] = BundleEntry(
        request=EntryRequest(method="POST", url="List"),
        resource=OperationOutcome.make_good_outcome("not a List"),
    )

    with caplog.at_level(logging.WARNING):
        result = _process(bundle_service, entry, index=0)

    assert result.response is not None
    assert result.response.status == "422"
    assert Log.REFERRAL_REGISTRATION_FAILED.event_id in [r.event_id for r in caplog.records if hasattr(r, "event_id")]
