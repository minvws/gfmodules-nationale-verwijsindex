import logging
from uuid import UUID, uuid4

import pytest

from app.debug.crypto_service_api_client_mock import CryptoServiceApiClientMock
from app.logging.events import Log
from app.models.fhir.resources.localization_list.request import LocalizationListParams
from app.models.ura import UraNumber
from app.services.exceptions import NotFoundError, UnauthorizedUraError
from app.services.fhir.localization_list import LocalizationListService
from app.services.key_info import KeyInfoService
from app.services.pseudonym_resolver import PseudonymResolver
from app.services.referral_service import ReferralService
from tests.conftest import TEST_PSEUDONYM_TOKEN, make_list_resource

AUTH_URA = UraNumber("00000001")
OTHER_URA = UraNumber("99999999")


@pytest.fixture()
def service(referral_service: ReferralService, key_info_service: KeyInfoService) -> LocalizationListService:
    key_info_service.add_one("nvi-label", "AES_CBC")
    resolver = PseudonymResolver(crypto_client=CryptoServiceApiClientMock(), key_info_service=key_info_service)
    return LocalizationListService(referral_service=referral_service, pseudonym_resolver=resolver)


def _params(subject: str | None = None, source: str | None = None) -> LocalizationListParams:
    return LocalizationListParams.model_construct(subject=subject, source=source)


def _event_ids(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [r.event_id for r in caplog.records if hasattr(r, "event_id")]


class TestCreate:
    def test_stores_and_returns_the_resource(self, service: LocalizationListService) -> None:
        result = service.create(make_list_resource(ura=str(AUTH_URA)), AUTH_URA, organization_name="Org")

        assert result.id is not None

    def test_rejects_a_resource_for_another_ura(
        self, service: LocalizationListService, caplog: pytest.LogCaptureFixture
    ) -> None:
        data = make_list_resource(ura=str(OTHER_URA))

        with caplog.at_level(logging.INFO), pytest.raises(UnauthorizedUraError):
            service.create(data, AUTH_URA, organization_name="Org")

        assert Log.REFERRAL_ACCESS_DENIED.event_id in _event_ids(caplog)

    def test_is_idempotent(self, service: LocalizationListService) -> None:
        first = service.create(make_list_resource(ura=str(AUTH_URA)), AUTH_URA, organization_name="Org")
        second = service.create(make_list_resource(ura=str(AUTH_URA)), AUTH_URA, organization_name="Org")

        assert second.id == first.id


class TestGet:
    def test_returns_the_stored_resource(self, service: LocalizationListService) -> None:
        created = service.create(make_list_resource(ura=str(AUTH_URA)), AUTH_URA, organization_name="Org")
        assert isinstance(created.id, UUID)

        assert service.get(created.id, AUTH_URA, organization_name="Org").id == created.id

    def test_hides_another_uras_resource_behind_not_found(
        self, service: LocalizationListService, caplog: pytest.LogCaptureFixture
    ) -> None:
        # Reported as 404 rather than 403 so a caller cannot probe for the existence of
        # another organization's records.
        created = service.create(make_list_resource(ura=str(AUTH_URA)), AUTH_URA, organization_name="Org")
        assert isinstance(created.id, UUID)

        with caplog.at_level(logging.INFO), pytest.raises(NotFoundError):
            service.get(created.id, OTHER_URA, organization_name="Other")

        assert Log.REFERRAL_ACCESS_DENIED.event_id in _event_ids(caplog)

    def test_raises_not_found_for_unknown_id(self, service: LocalizationListService) -> None:
        with pytest.raises(NotFoundError):
            service.get(uuid4(), AUTH_URA, organization_name="Org")


class TestQuery:
    def test_localize_hit_logs_success(
        self, service: LocalizationListService, caplog: pytest.LogCaptureFixture
    ) -> None:
        service.create(make_list_resource(ura=str(AUTH_URA)), AUTH_URA, organization_name="Org")

        with caplog.at_level(logging.INFO):
            bundle = service.query(_params(subject=TEST_PSEUDONYM_TOKEN), OTHER_URA, organization_name="Other")

        assert bundle.total == 1
        assert Log.LOCALIZATION_SUCCESS.event_id in _event_ids(caplog)

    def test_localize_miss_logs_no_match(
        self, service: LocalizationListService, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.INFO):
            bundle = service.query(_params(subject=TEST_PSEUDONYM_TOKEN), AUTH_URA, organization_name="Org")

        assert bundle.total == 0
        assert Log.LOCALIZATION_NO_MATCH.event_id in _event_ids(caplog)

    def test_non_localize_query_is_scoped_to_the_caller_ura(
        self, service: LocalizationListService, caplog: pytest.LogCaptureFixture
    ) -> None:
        service.create(make_list_resource(ura=str(AUTH_URA)), AUTH_URA, organization_name="Org")

        with caplog.at_level(logging.INFO):
            bundle = service.query(_params(source="SRC-001"), OTHER_URA, organization_name="Other")

        # Scoped to OTHER_URA, so the record created under AUTH_URA is not returned.
        assert bundle.total == 0
        assert Log.REFERRALS_QUERIED.event_id in _event_ids(caplog)

    def test_empty_query_returns_only_the_caller_records(self, service: LocalizationListService) -> None:
        service.create(make_list_resource(ura=str(AUTH_URA)), AUTH_URA, organization_name="Org")

        assert service.query(_params(), AUTH_URA, organization_name="Org").total == 1
        assert service.query(_params(), OTHER_URA, organization_name="Other").total == 0


class TestDelete:
    def test_deletes_and_reports_200(self, service: LocalizationListService) -> None:
        created = service.create(make_list_resource(ura=str(AUTH_URA)), AUTH_URA, organization_name="Org")
        assert isinstance(created.id, UUID)

        _, status = service.delete(created.id, AUTH_URA, organization_name="Org")

        assert status == 200

    def test_reports_404_when_nothing_was_deleted(self, service: LocalizationListService) -> None:
        created = service.create(make_list_resource(ura=str(AUTH_URA)), AUTH_URA, organization_name="Org")
        assert isinstance(created.id, UUID)

        outcome, status = service.delete(created.id, OTHER_URA, organization_name="Other")

        assert status == 404
        assert outcome.issue[0].code == "warning"


class TestDeleteByQuery:
    def test_deletes_by_subject_and_logs_patient_scope(
        self, service: LocalizationListService, caplog: pytest.LogCaptureFixture
    ) -> None:
        service.create(make_list_resource(ura=str(AUTH_URA)), AUTH_URA, organization_name="Org")

        with caplog.at_level(logging.INFO):
            _, status = service.delete_by_query(
                _params(subject=TEST_PSEUDONYM_TOKEN), AUTH_URA, organization_name="Org"
            )

        assert status == 200
        assert Log.ALL_PATIENT_REFERRALS_DELETED.event_id in _event_ids(caplog)

    def test_deletes_without_subject_and_logs_ura_scope(
        self, service: LocalizationListService, caplog: pytest.LogCaptureFixture
    ) -> None:
        service.create(make_list_resource(ura=str(AUTH_URA)), AUTH_URA, organization_name="Org")

        with caplog.at_level(logging.INFO):
            _, status = service.delete_by_query(_params(source="SRC-001"), AUTH_URA, organization_name="Org")

        assert status == 200
        assert Log.ALL_URA_REFERRALS_DELETED.event_id in _event_ids(caplog)

    def test_reports_not_found_when_nothing_matched(self, service: LocalizationListService) -> None:
        # A miss reports 404, the same way delete-by-id does, so both delete paths
        # behave alike.
        outcome, status = service.delete_by_query(_params(source="NOTHING"), AUTH_URA, organization_name="Org")

        assert status == 404
        assert outcome.issue[0].code == "not-found"

    def test_reports_the_deleted_count_on_success(self, service: LocalizationListService) -> None:
        service.create(make_list_resource(ura=str(AUTH_URA)), AUTH_URA, organization_name="Org")

        outcome, status = service.delete_by_query(_params(source="SRC-001"), AUTH_URA, organization_name="Org")

        assert status == 200
        assert outcome.issue[0].details is not None
        assert outcome.issue[0].details.text == "1 resources have been deleted successfully"

    def test_does_not_log_a_deletion_event_when_nothing_matched(
        self, service: LocalizationListService, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.INFO):
            service.delete_by_query(_params(source="NOTHING"), AUTH_URA, organization_name="Org")

        assert Log.ALL_PATIENT_REFERRALS_DELETED.event_id not in _event_ids(caplog)
        assert Log.ALL_URA_REFERRALS_DELETED.event_id not in _event_ids(caplog)
