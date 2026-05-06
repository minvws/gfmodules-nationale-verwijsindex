import pytest

from app.models.auth.data import AuthorizationRole
from app.models.auth.headers import AuthHeaders
from app.models.ura import UraNumber
from app.services.auth.exceptions import InvalidHeaderPropertyValue
from app.services.auth.header import AuthHeaderService


def test_validate_should_succeed(ura_number: UraNumber, auth_header_service: AuthHeaderService) -> None:
    expected = AuthHeaders(
        oin="oin123",
        source_id="source123",
        ura=ura_number.value,
        audience=auth_header_service.config.audience,
        authorized_role=AuthorizationRole.CONSULTING.value,
        scope=["nvi:read"],
        cert_type="oin",
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
        authorized_role=AuthorizationRole.CONSULTING.value,
        scope=["nvi:read"],
        cert_type="oin",
    )

    with pytest.raises(InvalidHeaderPropertyValue) as exec:
        auth_header_service.validate(data)

    assert f"Invalid header property audience with value {data.audience}" in str(exec.value.detail)

    assert exec.value.status_code == 401
