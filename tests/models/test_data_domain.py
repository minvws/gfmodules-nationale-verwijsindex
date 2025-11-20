from app.models.data_domain import DataDomain


def test_init_should_converts_value_to_string() -> None:
    expected = "123"
    actual = DataDomain(123)
    assert actual.value == expected


def test_class_should_return_value_as_str() -> None:
    expected = "ImagingStudy"
    actual = DataDomain("ImagingStudy")
    assert str(actual) == expected


def test_repr_format_should_succeed() -> None:
    expected = "DataDomain(MedicationStatement)"
    actual = DataDomain("MedicationStatement")
    assert repr(actual) == expected


def test_equality_should_succeed_with_same_value() -> None:
    domain_1 = DataDomain("abc")
    domain_2 = DataDomain("abc")
    assert domain_1 == domain_2


def test_inequality_should_succeed_with_different_value() -> None:
    domain_1 = DataDomain("abc")
    domain_2 = DataDomain("xyz")
    assert domain_1 != domain_2


def test_equality_should_return_false_when_compared_with_non_instance() -> None:
    domain = DataDomain("test")
    assert domain != "test"
