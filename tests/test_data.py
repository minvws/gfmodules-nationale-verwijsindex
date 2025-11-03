import pytest

from app.data import UraNumber


def test_ura_number() -> None:
    assert "00001234" == str(UraNumber("1234"))
    assert "12345678" == str(UraNumber("12345678"))

    with pytest.raises(ValueError):
        UraNumber("1234567890")
    with pytest.raises(ValueError):
        UraNumber("foobar")
    with pytest.raises(ValueError):
        UraNumber("1A525")
    with pytest.raises(ValueError):
        UraNumber("")
