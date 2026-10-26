from collections.abc import Callable
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from opentelemetry.sdk.metrics.export import HistogramDataPoint

from app.debug.crypto_service_api_client_mock import CryptoServiceApiClientMock
from app.models.auth.context import AuthContext
from app.services.key_info import KeyInfoService
from app.services.referral_service import ReferralService
from tests.conftest import TEST_PSEUDONYM_TOKEN, CounterValue, MetricPoints
from tests.routers.conftest import (
    TEST_SOURCE_ID,
    TEST_URA,
    make_auth_context,
    make_localize_auth_context,
    make_test_client,
)

REGISTRATION = {"pseudonym": "pseu", "oprf_key": "k"}


@pytest.fixture
def count(counter_value: CounterValue) -> Callable[[str, str], int]:
    return lambda operation, ura: counter_value("nvi_operations", {"operation": operation, "ura": ura})


@pytest.fixture
def client_for(
    referral_service: ReferralService,
    crypto_client: CryptoServiceApiClientMock,
    key_info_service: KeyInfoService,
) -> Callable[[AuthContext], TestClient]:
    return lambda ctx: make_test_client(referral_service, crypto_client, key_info_service, ctx)


def test_registrations_and_deletions_count_stored_rows(
    client_for: Callable[[AuthContext], TestClient],
    key_info_service: KeyInfoService,
    count: Callable[[str, str], int],
) -> None:
    key_info_service.add_one("nvi-label", "AES_CBC")
    client = client_for(make_auth_context())

    for pseudonym in ("p1", "p2", "p3", "p1"):
        client.post("/registrations", json={"pseudonym": pseudonym, "oprf_key": "k"})
    client.delete("/fhir/List", params={"source:identifier": TEST_SOURCE_ID})

    assert count("registration", TEST_URA) == 3
    assert count("deletion", TEST_URA) == 3


def test_localization_counts_requester_and_referrals_found(
    client_for: Callable[[AuthContext], TestClient],
    key_info_service: KeyInfoService,
    metric_points: MetricPoints,
    count: Callable[[str, str], int],
) -> None:
    key_info_service.add_one("nvi-label", "AES_CBC")
    for ura in ("00000002", "00000003"):
        client_for(make_auth_context(ura=ura)).post("/registrations", json=REGISTRATION)
    localizer = client_for(make_localize_auth_context())

    localizer.post("/localize", json=REGISTRATION)
    localizer.get("/fhir/List", params={"subject:identifier": TEST_PSEUDONYM_TOKEN})

    operations = [dict(point.attributes or {}) for point in metric_points("nvi_operations")]
    (referrals,) = metric_points("nvi_localization_referrals")
    assert isinstance(referrals, HistogramDataPoint)
    assert count("localization", TEST_URA) == 2
    assert {attributes["ura"] for attributes in operations if attributes["operation"] == "localization"} == {TEST_URA}
    assert all(set(attributes) == {"operation", "ura"} for attributes in operations)
    assert not referrals.attributes
    assert (referrals.count, referrals.sum, referrals.bucket_counts[0]) == (2, 2, 1)
    assert list(referrals.explicit_bounds) == [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20, 50]
    values = [str(value) for attributes in operations for value in attributes.values()]
    assert not any(secret in value for value in values for secret in ("pseu", TEST_PSEUDONYM_TOKEN, TEST_SOURCE_ID))


def test_failures_and_own_reads_record_nothing(
    client_for: Callable[[AuthContext], TestClient],
    key_info_service: KeyInfoService,
    metric_points: MetricPoints,
) -> None:
    client = client_for(make_auth_context())

    assert client.post("/registrations", json=REGISTRATION).status_code == 503
    assert client_for(make_localize_auth_context()).post("/localize", json=REGISTRATION).status_code == 503
    key_info_service.add_one("nvi-label", "AES_CBC")
    client.get("/registrations", params=REGISTRATION)
    client.get("/fhir/List", params={"source:identifier": TEST_SOURCE_ID})
    assert client.delete(f"/fhir/List/{uuid4()}").status_code == 404

    assert metric_points("nvi_operations") == []
    assert metric_points("nvi_localization_referrals") == []
