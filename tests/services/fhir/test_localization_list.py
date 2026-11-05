import logging
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from app.logging.events import Log
from app.models.fhir.bundle import Bundle
from app.models.fhir.resources.localization_list.request import (
    COUNT_PARAM,
    DEVICE_IDENTIFIER_PARAM,
    OFFSET_PARAM,
    SUBJECT_IDENTIFIER_PARAM,
    LocalizationListSearchParams,
)
from app.models.fhir.resources.localization_list.resource import LocalizationList
from app.models.ura import UraNumber
from app.services.exceptions import NotFoundError, PseudonymError, UnauthorizedUraError
from app.services.fhir.localization_list import LocalizationListService
from app.services.key_info import KeyInfoService
from app.services.pseudonym_referral_service import PseudonymReferralService
from app.services.referral_service import ReferralService
from tests.conftest import TEST_PSEUDONYM_TOKEN, make_list_resource

AUTH_URA = UraNumber("00000001")
OTHER_URA = UraNumber("99999999")
AUTH_SOURCE = "SRC-001"
OTHER_SOURCE = "SRC-002"
INVALID_PSEUDONYM_TOKEN = "not-a-valid-token!!!"


@pytest.fixture()
def service(
    referral_service: ReferralService,
    pseudonym_referral_service: PseudonymReferralService,
    key_info_service: KeyInfoService,
) -> LocalizationListService:
    key_info_service.add_one("nvi-label", "AES_CBC")
    return LocalizationListService(
        referral_service=referral_service, pseudonym_referral_service=pseudonym_referral_service
    )


def _params(
    subject: str | None = None,
    source: str | None = None,
    count: int | None = None,
    offset: int = 0,
) -> LocalizationListSearchParams:
    return LocalizationListSearchParams.model_validate(
        {SUBJECT_IDENTIFIER_PARAM: subject, DEVICE_IDENTIFIER_PARAM: source, COUNT_PARAM: count, OFFSET_PARAM: offset}
    )


def _create_referrals(service: LocalizationListService, amount: int) -> None:
    """Create referrals for AUTH_URA, one per source, as a pseudonym can only be registered once per source."""
    for i in range(amount):
        service.create(make_list_resource(ura=str(AUTH_URA), source_id=f"SRC-{i:03}"), AUTH_URA)


def _links(bundle: Bundle[LocalizationList]) -> dict[str, str]:
    return {link.relation: link.url for link in bundle.link or []}


def _event_ids(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [r.event_id for r in caplog.records if hasattr(r, "event_id")]


class TestCreate:
    def test_stores_and_returns_the_resource(self, service: LocalizationListService) -> None:
        result, _ = service.create(make_list_resource(ura=str(AUTH_URA)), AUTH_URA)

        assert result.id is not None

    @pytest.mark.parametrize("pseudonym", [TEST_PSEUDONYM_TOKEN, INVALID_PSEUDONYM_TOKEN], ids=["valid", "invalid"])
    def test_rejects_a_resource_for_another_ura(
        self, service: LocalizationListService, caplog: pytest.LogCaptureFixture, pseudonym: str
    ) -> None:
        data = make_list_resource(ura=str(OTHER_URA), pseudonym=pseudonym)

        with caplog.at_level(logging.INFO), pytest.raises(UnauthorizedUraError):
            service.create(data, AUTH_URA)

        assert _event_ids(caplog) == [Log.REFERRAL_ACCESS_DENIED.event_id]

    def test_rejects_an_invalid_pseudonym_without_a_failure_event(
        self, service: LocalizationListService, caplog: pytest.LogCaptureFixture
    ) -> None:
        data = make_list_resource(ura=str(AUTH_URA), pseudonym=INVALID_PSEUDONYM_TOKEN)

        with caplog.at_level(logging.INFO), pytest.raises(PseudonymError, match="List.subject.identifier.value"):
            service.create(data, AUTH_URA)

        assert _event_ids(caplog) == []

    def test_is_idempotent(self, service: LocalizationListService) -> None:
        first, first_created = service.create(make_list_resource(ura=str(AUTH_URA)), AUTH_URA)
        second, second_created = service.create(make_list_resource(ura=str(AUTH_URA)), AUTH_URA)

        assert first_created is True
        assert second_created is False

        assert second.id == first.id


class TestGet:
    def test_returns_the_stored_resource(self, service: LocalizationListService) -> None:
        created, _ = service.create(make_list_resource(ura=str(AUTH_URA)), AUTH_URA)
        assert isinstance(created.id, UUID)

        assert service.get(created.id, AUTH_URA).id == created.id

    def test_hides_another_uras_resource_behind_not_found(
        self, service: LocalizationListService, caplog: pytest.LogCaptureFixture
    ) -> None:
        created, _ = service.create(make_list_resource(ura=str(AUTH_URA)), AUTH_URA)
        assert isinstance(created.id, UUID)

        with caplog.at_level(logging.INFO), pytest.raises(NotFoundError):
            service.get(created.id, OTHER_URA)

        assert Log.REFERRAL_ACCESS_DENIED.event_id in _event_ids(caplog)
        assert Log.REFERRAL_SEARCHED_ON_ID.event_id not in _event_ids(caplog)

    def test_raises_not_found_for_unknown_id(self, service: LocalizationListService) -> None:
        with pytest.raises(NotFoundError):
            service.get(uuid4(), AUTH_URA)


class TestQuery:
    def test_localize_hit_logs_success(
        self, service: LocalizationListService, caplog: pytest.LogCaptureFixture
    ) -> None:
        service.create(make_list_resource(ura=str(AUTH_URA)), AUTH_URA)

        with caplog.at_level(logging.INFO):
            bundle = service.query(_params(subject=TEST_PSEUDONYM_TOKEN), OTHER_URA)

        assert bundle.total == 1
        assert Log.LOCALIZATION_SUCCESS.event_id in _event_ids(caplog)

    def test_localize_miss_logs_no_match(
        self, service: LocalizationListService, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.INFO):
            bundle = service.query(_params(subject=TEST_PSEUDONYM_TOKEN), AUTH_URA)

        assert bundle.total == 0
        assert Log.LOCALIZATION_NO_MATCH.event_id in _event_ids(caplog)

    @pytest.mark.parametrize("source", [None, AUTH_SOURCE], ids=["localize", "own-source"])
    def test_rejects_an_invalid_pseudonym_without_a_failure_event(
        self, source: str | None, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.INFO), pytest.raises(ValidationError, match="subject:identifier"):
            _params(subject=INVALID_PSEUDONYM_TOKEN, source=source)

        assert _event_ids(caplog) == []

    def test_non_localize_query_is_scoped_to_the_caller_ura(
        self, service: LocalizationListService, caplog: pytest.LogCaptureFixture
    ) -> None:
        service.create(make_list_resource(ura=str(AUTH_URA)), AUTH_URA)

        with caplog.at_level(logging.INFO):
            bundle = service.query(_params(source="SRC-001"), OTHER_URA)

        assert bundle.total == 0
        assert Log.REFERRALS_QUERIED.event_id in _event_ids(caplog)

    def test_empty_query_returns_only_the_caller_records(self, service: LocalizationListService) -> None:
        service.create(make_list_resource(ura=str(AUTH_URA)), AUTH_URA)

        assert service.query(_params(), AUTH_URA).total == 1
        assert service.query(_params(), OTHER_URA).total == 0


class TestQueryPagination:
    def test_uses_the_default_page_size(
        self, referral_service: ReferralService, service: LocalizationListService
    ) -> None:
        paged = LocalizationListService(
            referral_service=referral_service,
            pseudonym_referral_service=service.pseudonym_referral_service,
            default_page_size=2,
            max_page_size=10,
        )
        _create_referrals(paged, 3)

        bundle = paged.query(_params(), AUTH_URA)

        assert bundle.total == 3
        assert len(bundle.entry) == 2

    def test_caps_the_requested_page_size(
        self, referral_service: ReferralService, service: LocalizationListService
    ) -> None:
        paged = LocalizationListService(
            referral_service=referral_service,
            pseudonym_referral_service=service.pseudonym_referral_service,
            default_page_size=1,
            max_page_size=2,
        )
        _create_referrals(paged, 3)

        bundle = paged.query(_params(count=50), AUTH_URA, request_url="List")

        assert len(bundle.entry) == 2
        assert _links(bundle)["self"] == "List?_count=2&_offset=0"

    def test_total_counts_all_matches_while_entries_hold_the_page(self, service: LocalizationListService) -> None:
        _create_referrals(service, 5)

        bundle = service.query(_params(count=2, offset=4), AUTH_URA)

        assert bundle.total == 5
        assert len(bundle.entry) == 1

    def test_pages_do_not_overlap(self, service: LocalizationListService) -> None:
        _create_referrals(service, 5)

        devices = [
            entry.resource.get_device()
            for offset in (0, 2, 4)
            for entry in service.query(_params(count=2, offset=offset), AUTH_URA).entry
            if entry.resource is not None
        ]

        assert sorted(devices) == [f"SRC-{i:03}" for i in range(5)]

    def test_omits_links_without_a_request_url(self, service: LocalizationListService) -> None:
        _create_referrals(service, 1)

        assert service.query(_params(), AUTH_URA).link is None

    def test_first_page_links_to_the_next_page(self, service: LocalizationListService) -> None:
        _create_referrals(service, 5)

        bundle = service.query(_params(count=2), AUTH_URA, request_url="List")

        assert _links(bundle) == {
            "self": "List?_count=2&_offset=0",
            "next": "List?_count=2&_offset=2",
        }

    def test_middle_page_links_both_ways(self, service: LocalizationListService) -> None:
        _create_referrals(service, 5)

        bundle = service.query(_params(count=2, offset=2), AUTH_URA, request_url="List")

        assert _links(bundle) == {
            "self": "List?_count=2&_offset=2",
            "next": "List?_count=2&_offset=4",
            "previous": "List?_count=2&_offset=0",
        }

    def test_last_page_links_only_back(self, service: LocalizationListService) -> None:
        _create_referrals(service, 5)

        bundle = service.query(_params(count=2, offset=4), AUTH_URA, request_url="List")

        assert _links(bundle) == {
            "self": "List?_count=2&_offset=4",
            "previous": "List?_count=2&_offset=2",
        }

    def test_previous_link_does_not_go_below_zero(self, service: LocalizationListService) -> None:
        _create_referrals(service, 5)

        bundle = service.query(_params(count=2, offset=1), AUTH_URA, request_url="List")

        assert _links(bundle)["previous"] == "List?_count=2&_offset=0"

    def test_links_keep_the_search_parameters(self, service: LocalizationListService) -> None:
        _create_referrals(service, 1)

        bundle = service.query(
            _params(source="SRC-000", count=5, offset=0),
            AUTH_URA,
            request_url="https://nvi.example/fhir/List?source%3Aidentifier=SRC-000&_count=5&_offset=0",
        )

        assert _links(bundle) == {
            "self": "https://nvi.example/fhir/List?source%3Aidentifier=SRC-000&_count=5&_offset=0",
        }

    def test_localize_logs_the_total_instead_of_the_page_size(
        self, service: LocalizationListService, caplog: pytest.LogCaptureFixture
    ) -> None:
        _create_referrals(service, 3)

        with caplog.at_level(logging.INFO):
            service.query(_params(subject=TEST_PSEUDONYM_TOKEN, count=1), OTHER_URA)

        counts = [
            getattr(r, "result_count", None)
            for r in caplog.records
            if getattr(r, "event_id", None) == Log.LOCALIZATION_SUCCESS.event_id
        ]
        assert counts == [3]

    def test_localize_beyond_the_last_page_still_counts_as_a_hit(
        self, service: LocalizationListService, caplog: pytest.LogCaptureFixture
    ) -> None:
        _create_referrals(service, 1)

        with caplog.at_level(logging.INFO):
            bundle = service.query(_params(subject=TEST_PSEUDONYM_TOKEN, offset=10), OTHER_URA)

        assert bundle.entry == []
        assert Log.LOCALIZATION_SUCCESS.event_id in _event_ids(caplog)


class TestDelete:
    def test_deletes_and_reports_success(self, service: LocalizationListService) -> None:
        created, _ = service.create(make_list_resource(ura=str(AUTH_URA)), AUTH_URA)
        assert isinstance(created.id, UUID)

        outcome = service.delete(created.id, AUTH_URA, AUTH_SOURCE)

        assert outcome.issue[0].code == "informational"
        assert service.query(_params(), AUTH_URA).total == 0

    def test_hides_another_uras_resource_behind_not_found(self, service: LocalizationListService) -> None:
        created, _ = service.create(make_list_resource(ura=str(AUTH_URA)), AUTH_URA)
        assert isinstance(created.id, UUID)

        with pytest.raises(NotFoundError):
            service.delete(created.id, OTHER_URA, AUTH_SOURCE)

    def test_hides_another_sources_resource_behind_not_found(self, service: LocalizationListService) -> None:
        created, _ = service.create(make_list_resource(ura=str(AUTH_URA)), AUTH_URA)
        assert isinstance(created.id, UUID)

        with pytest.raises(NotFoundError):
            service.delete(created.id, AUTH_URA, OTHER_SOURCE)

        assert service.query(_params(), AUTH_URA).total == 1

    def test_raises_not_found_for_unknown_id(self, service: LocalizationListService) -> None:
        with pytest.raises(NotFoundError):
            service.delete(uuid4(), AUTH_URA, AUTH_SOURCE)


class TestDeleteByQuery:
    def test_deletes_by_subject_and_logs_patient_scope(
        self, service: LocalizationListService, caplog: pytest.LogCaptureFixture
    ) -> None:
        service.create(make_list_resource(ura=str(AUTH_URA)), AUTH_URA)

        with caplog.at_level(logging.INFO):
            _, status = service.delete_by_query(_params(subject=TEST_PSEUDONYM_TOKEN), AUTH_URA, AUTH_SOURCE)

        assert status == 200
        assert Log.ALL_PATIENT_REFERRALS_DELETED.event_id in _event_ids(caplog)

    def test_deletes_without_subject_and_logs_ura_scope(
        self, service: LocalizationListService, caplog: pytest.LogCaptureFixture
    ) -> None:
        service.create(make_list_resource(ura=str(AUTH_URA)), AUTH_URA)

        with caplog.at_level(logging.INFO):
            _, status = service.delete_by_query(_params(), AUTH_URA, AUTH_SOURCE)

        assert status == 200
        assert Log.ALL_URA_REFERRALS_DELETED.event_id in _event_ids(caplog)

    def test_is_scoped_to_the_callers_own_source(self, service: LocalizationListService) -> None:
        service.create(make_list_resource(ura=str(AUTH_URA), source_id=AUTH_SOURCE), AUTH_URA)
        service.create(make_list_resource(ura=str(AUTH_URA), source_id=OTHER_SOURCE), AUTH_URA)

        _, status = service.delete_by_query(_params(subject=TEST_PSEUDONYM_TOKEN), AUTH_URA, AUTH_SOURCE)

        assert status == 200
        # The sibling source's referral for the same URA and pseudonym survives.
        remaining = service.query(_params(), AUTH_URA)
        assert remaining.total == 1
        assert remaining.entry[0].resource is not None
        assert remaining.entry[0].resource.get_device() == OTHER_SOURCE

    def test_reports_not_found_when_nothing_matched(self, service: LocalizationListService) -> None:
        outcome, status = service.delete_by_query(_params(), AUTH_URA, "NOTHING")

        assert status == 404
        assert outcome.issue[0].code == "not-found"

    def test_reports_the_deleted_count_on_success(self, service: LocalizationListService) -> None:
        service.create(make_list_resource(ura=str(AUTH_URA)), AUTH_URA)

        outcome, status = service.delete_by_query(_params(), AUTH_URA, AUTH_SOURCE)

        assert status == 200
        assert outcome.issue[0].details is not None
        assert outcome.issue[0].details.text == "1 resources have been deleted successfully"

    def test_does_not_log_a_deletion_event_when_nothing_matched(
        self, service: LocalizationListService, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.INFO):
            service.delete_by_query(_params(), AUTH_URA, "NOTHING")

        assert Log.ALL_PATIENT_REFERRALS_DELETED.event_id not in _event_ids(caplog)
        assert Log.ALL_URA_REFERRALS_DELETED.event_id not in _event_ids(caplog)
