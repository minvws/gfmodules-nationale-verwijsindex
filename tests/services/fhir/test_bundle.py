import logging
from typing import Any, Literal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models.auth.context import AuthContext, AuthenticationClaims
from app.models.auth.data import AuthorizationScope
from app.models.fhir.bundle import Bundle, BundleEntry, EntryRequest
from app.models.fhir.resources.localization_list.request import LocalizationListSearchParams
from app.models.fhir.resources.localization_list.resource import LocalizationList
from app.models.fhir.resources.operation_outcome.resource import OperationOutcome
from app.models.ura import UraNumber
from app.services.exceptions import BundleTooLargeError, InvalidModelError
from app.services.fhir.bundle import BundleService
from app.services.fhir.localization_list import LocalizationListService
from app.services.key_info import KeyInfoService
from app.services.pseudonym_referral_service import PseudonymReferralService
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
            oin="00000000000000000001",
            acting_organization_name="client.example.nl",
            source_id=TEST_SOURCE_ID,
        ),
        scope=ALL_SCOPES,
        audience="nvi.service",
    )
    return bundle_service.process_entry(ctx=ctx, entry=entry, index=index)


@pytest.fixture()
def bundle_service(
    referral_service: ReferralService,
    pseudonym_referral_service: PseudonymReferralService,
) -> BundleService:
    localization_service = LocalizationListService(
        referral_service=referral_service, pseudonym_referral_service=pseudonym_referral_service
    )
    return BundleService(localization_service, max_entries=2)


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
    assert result.response.status == "201"
    assert result.resource is not None
    assert result.resource.id is not None


def test_post_of_an_existing_resource_returns_200(
    bundle_service: BundleService, key_info_service: KeyInfoService
) -> None:
    key_info_service.add_one("nvi-label", "AES_CBC")
    entry: BundleEntry[LocalizationList] = BundleEntry(
        request=EntryRequest(method="POST", url="List"),
        resource=make_list_resource(ura=str(AUTH_URA)),
    )

    first = _process(bundle_service, entry, index=0)
    second = _process(bundle_service, entry, index=1)

    assert second.response is not None
    assert second.response.status == "200"
    assert first.resource is not None
    assert second.resource is not None
    assert second.resource.id == first.resource.id


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


@pytest.mark.parametrize(
    ("entry", "code"),
    [
        (BundleEntry(), "required"),
        (_entry("POST", "List"), "required"),
        (_entry("GET", "http://["), "invalid"),
        (_entry("GET", f"Patient/{uuid4()}"), "not-supported"),
        (_entry("GET", f"List/{uuid4()}?source:identifier=SRC-001"), "not-supported"),
    ],
    ids=["missing-request", "missing-resource", "malformed-url", "unsupported-resource", "id-and-params"],
)
def test_rejects_an_invalid_entry_with_its_issue_code(
    bundle_service: BundleService, entry: BundleEntry[LocalizationList], code: str
) -> None:
    result = _process(bundle_service, entry, index=0)

    assert result.response is not None
    assert result.response.status == "422"
    assert result.response.outcome is not None
    assert result.response.outcome.issue[0].code == code


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
    def test_empty_bundle_is_invalid(self, bundle_service: BundleService) -> None:
        with pytest.raises(InvalidModelError):
            bundle_service.validate_entry_count(Bundle(entry=[]))

    def test_bundle_up_to_the_maximum_is_valid(self, bundle_service: BundleService) -> None:
        bundle_service.validate_entry_count(Bundle(entry=[BundleEntry(), BundleEntry()]))

    def test_bundle_over_the_maximum_is_too_large(self, bundle_service: BundleService) -> None:
        with pytest.raises(BundleTooLargeError, match="maximum of 2 entries"):
            bundle_service.validate_entry_count(Bundle(entry=[BundleEntry(), BundleEntry(), BundleEntry()]))


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
        assert result.response.status == "200"

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
        assert result.response.status == "200"


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

        with caplog.at_level(logging.INFO):
            result = _process(bundle_service, entry, index=0)

        assert result.response is not None
        assert result.response.status == "422"
        assert "Request rejected with 422 (PseudonymError)" in caplog.text

    def test_query_with_malformed_pseudonym_maps_to_422_without_rejection_log(
        self,
        bundle_service: BundleService,
        key_info_service: KeyInfoService,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        key_info_service.add_one("nvi-label", "AES_CBC")

        with caplog.at_level(logging.INFO):
            result = _process(bundle_service, _entry("GET", "List?subject:identifier=not-a-valid-token!!!"), index=0)

        assert result.response is not None
        assert result.response.status == "422"
        assert result.response.outcome is not None
        assert result.response.outcome.issue[0].code == "invalid"
        assert "not-a-valid-token!!!" not in str(result.response.outcome.model_dump())
        assert "Request rejected with 422 (ValidationError)" not in caplog.text

    @pytest.mark.parametrize("url", ["List?_count=0", "List?source:identifier=wrong-system|value"])
    def test_invalid_query_parameters_map_to_invalid(self, bundle_service: BundleService, url: str) -> None:
        result = _process(bundle_service, _entry("GET", url), index=0)

        assert result.response is not None
        assert result.response.status == "422"
        assert result.response.outcome is not None
        assert result.response.outcome.issue[0].code == "invalid"

    @pytest.mark.parametrize(
        ("params", "expected_code"),
        [({}, "required"), ({"_count": "0"}, "invalid")],
        ids=["missing", "missing-and-invalid"],
    )
    def test_parameter_validation_classifies_missing_and_invalid_errors(
        self, params: dict[str, str], expected_code: str
    ) -> None:
        class RequiredSearchParams(LocalizationListSearchParams):
            required_value: str

        with pytest.raises(ValidationError) as caught:
            RequiredSearchParams.model_validate(params)

        result = BundleService._invalid_query_entry(0, caught.value)

        assert isinstance(result, BundleEntry)
        assert result.response is not None
        assert result.response.status == "422"
        assert result.response.outcome is not None
        assert result.response.outcome.issue[0].code == expected_code

    @pytest.mark.parametrize(
        ("scope", "status"),
        [(AuthorizationScope.READ, "403"), (AuthorizationScope.LOCALIZE, "422")],
    )
    def test_invalid_subject_with_own_source_uses_existing_scope_fallback(
        self, bundle_service: BundleService, scope: AuthorizationScope, status: str
    ) -> None:
        ctx = AuthContext(
            claims=AuthenticationClaims(
                ura_number=AUTH_URA,
                organization_name="Org",
                oin="00000000000000000001",
                acting_organization_name="client.example.nl",
                source_id=TEST_SOURCE_ID,
            ),
            scope=[scope],
            audience="nvi.service",
        )
        url = f"List?subject:identifier=not-a-valid-token!!!&source:identifier={TEST_SOURCE_ID}"

        result = bundle_service.process_entry(ctx=ctx, entry=_entry("GET", url), index=0)

        assert result.response is not None
        assert result.response.status == status
        assert result.response.outcome is not None
        if status == "422":
            assert result.response.outcome.issue[0].code == "invalid"
        assert "not-a-valid-token!!!" not in str(result.response.outcome.model_dump())

    def test_invalid_subject_system_keeps_stricter_scope_requirement(self, bundle_service: BundleService) -> None:
        ctx = AuthContext(
            claims=AuthenticationClaims(
                ura_number=AUTH_URA,
                organization_name="Org",
                oin="00000000000000000001",
                acting_organization_name="client.example.nl",
                source_id=TEST_SOURCE_ID,
            ),
            scope=[AuthorizationScope.READ],
            audience="nvi.service",
        )
        url = f"List?subject:identifier=wrong-system|value&source:identifier={TEST_SOURCE_ID}"

        result = bundle_service.process_entry(ctx=ctx, entry=_entry("GET", url), index=0)

        assert result.response is not None
        assert result.response.status == "403"

    def test_read_of_an_unknown_id_logs_no_event(
        self, bundle_service: BundleService, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.WARNING):
            result = _process(bundle_service, _entry("GET", f"List/{uuid4()}"), index=0)

        assert result.response is not None
        assert result.response.status == "404"
        assert [r.event_id for r in caplog.records if hasattr(r, "event_id")] == []


def test_post_with_a_non_list_resource_returns_validation_response(bundle_service: BundleService) -> None:
    entry: BundleEntry[Any] = BundleEntry(
        request=EntryRequest(method="POST", url="List"),
        resource=OperationOutcome.make_good_outcome("not a List"),
    )

    result = _process(bundle_service, entry, index=0)

    assert result.response is not None
    assert result.response.status == "422"
