import pytest

from app.models.auth.headers import AuthHeaders
from app.models.ura import UraNumber
from app.services.auth.header import AuthHeaderService
from app.services.exceptions import InvalidHeaderPropertyError


def test_validate_should_succeed(ura_number: UraNumber, auth_header_service: AuthHeaderService) -> None:
    expected = AuthHeaders(
        oin="oin123",
        source_id="source123",
        ura=ura_number.value,
        audience=auth_header_service.expected_audiences[0],
        scope="nvi:read",
        cert_type="oin",
        organization_name="Test Organization",
    )

    actual = auth_header_service.validate(expected)

    assert expected == actual


def test_validate_should_panic_with_invalid_audience(
    ura_number: UraNumber, auth_header_service: AuthHeaderService
) -> None:
    data = AuthHeaders(
        oin="oin123",
        source_id="source123",
        ura=ura_number.value,
        audience="some-invalid-audience",
        scope="nvi:read",
        cert_type="oin",
        organization_name="Test Organization",
    )

    with pytest.raises(InvalidHeaderPropertyError) as exec:
        auth_header_service.validate(data)

    assert f"Invalid header property audience: unrecognized `{data.audience}`" in str(exec.value)
