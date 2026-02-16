from typing import Any, Dict

import pytest

from app.models.fhir.elements import Coding
from app.models.fhir.resources.data import CARE_CONTEXT_SYSTEM
from app.models.fhir.resources.organization.parameters import (
    CareContextParameter,
    OprfKeyParameter,
    OrganizationLocalizationDto,
    Parameters,
    PseudonymParamter,
    SourceTypeParameter,
)


@pytest.fixture()
def pseudonym_param() -> PseudonymParamter:
    return PseudonymParamter(value_string="some-pseudonym")


@pytest.fixture()
def oprf_key_param() -> OprfKeyParameter:
    return OprfKeyParameter(value_string="some-key")


@pytest.fixture()
def care_context_param() -> CareContextParameter:
    return CareContextParameter(
        name="careContext",
        value_coding=Coding(system=CARE_CONTEXT_SYSTEM, code="ImagingStudy"),
    )


@pytest.fixture()
def source_type_param() -> SourceTypeParameter:
    return SourceTypeParameter(value_code="hospital")


@pytest.fixture()
def mock_parameter(
    pseudonym_param: PseudonymParamter,
    oprf_key_param: OprfKeyParameter,
    care_context_param: CareContextParameter,
    source_type_param: SourceTypeParameter,
) -> Parameters:
    return Parameters(
        parameter=[
            pseudonym_param,
            oprf_key_param,
            care_context_param,
            source_type_param,
        ]
    )


def test_create_care_context_paramter_should_fail_with_non_valid_coding() -> None:
    data = {
        "name": "careContext",
        "valueConding": {
            "system": CARE_CONTEXT_SYSTEM,
            "someProperty": "I am an invalid property",
        },
    }
    with pytest.raises(ValueError):
        CareContextParameter.model_validate(data)


def test_create_care_context_parameter_should_fail_with_incorrect_system() -> None:
    data = {
        "name": "careContext",
        "valueCoding": {"system": "Some Invalid System", "code": "ImagingStudy"},
    }
    with pytest.raises(ValueError):
        CareContextParameter.model_validate(data)


def test_serialize_paramters_should_succeed(mock_parameter: Parameters) -> None:
    expected = {
        "resourceType": "Parameters",
        "parameter": [
            {"name": "pseudonym", "valueString": "some-pseudonym"},
            {"name": "oprfKey", "valueString": "some-key"},
            {
                "name": "careContext",
                "valueCoding": {"system": CARE_CONTEXT_SYSTEM, "code": "ImagingStudy"},
            },
            {"name": "sourceType", "valueCode": "hospital"},
        ],
    }

    actual = mock_parameter.model_dump(by_alias=True, exclude_none=True)

    assert expected == actual


def test_deserialize_should_succeed(mock_parameter: Parameters) -> None:
    data = {
        "resourceType": "Parameters",
        "parameter": [
            {"name": "pseudonym", "valueString": "some-pseudonym"},
            {"name": "oprfKey", "valueString": "some-key"},
            {
                "name": "careContext",
                "valueCoding": {"system": CARE_CONTEXT_SYSTEM, "code": "ImagingStudy"},
            },
            {"name": "sourceType", "valueCode": "hospital"},
        ],
    }
    actual = Parameters.model_validate(data)

    assert actual == mock_parameter


@pytest.mark.parametrize(
    "data",
    [
        {
            "resourceType": "Parameters",
            "parameter": [
                {"name": "pseudonym", "valueString": "some-pseudonym"},
                {"name": "pseudonym", "valueString": "Duplicate Pseudonym"},
                {"name": "oprfKey", "valueString": "some-key"},
                {
                    "name": "careContext",
                    "valueCoding": {
                        "system": CARE_CONTEXT_SYSTEM,
                        "code": "ImagingStudy",
                    },
                },
                {"name": "sourceType", "valueCode": "hospital"},
            ],
        },
        {
            "resourceType": "Parameters",
            "parameter": [
                {"name": "pseudonym", "valueString": "some-pseudonym"},
                {"name": "oprfKey", "valueString": "some-key"},
                {"name": "oprfKey", "valueString": "Duplicate Key"},
                {
                    "name": "careContext",
                    "valueCoding": {
                        "system": CARE_CONTEXT_SYSTEM,
                        "code": "ImagingStudy",
                    },
                },
                {"name": "sourceType", "valueCode": "hospital"},
            ],
        },
        {
            "resourceType": "Parameters",
            "parameter": [
                {"name": "pseudonym", "valueString": "some-pseudonym"},
                {"name": "oprfKey", "valueString": "some-key"},
                {
                    "name": "careContext",
                    "valueCoding": {
                        "system": CARE_CONTEXT_SYSTEM,
                        "code": "ImagingStudy",
                    },
                },
                {
                    "name": "careContext",
                    "valueCoding": {
                        "system": CARE_CONTEXT_SYSTEM,
                        "code": "ImagingStudy",
                    },
                },
                {"name": "sourceType", "valueCode": "hospital"},
            ],
        },
    ],
)
def test_validate_paramters_should_raise_exception_when_params_exceed_max_requirements(
    data: Dict[str, Any],
) -> None:
    with pytest.raises(ValueError):
        Parameters.model_validate(data)


@pytest.mark.parametrize(
    "data",
    [
        {
            "resourceType": "Parameters",
            "parameter": [
                {"name": "oprfKey", "valueString": "some-key"},
                {
                    "name": "careContext",
                    "valueCoding": {
                        "system": CARE_CONTEXT_SYSTEM,
                        "code": "ImagingStudy",
                    },
                },
                {"name": "sourceType", "valueCode": "hospital"},
            ],
        },
        {
            "resourceType": "Parameters",
            "parameter": [
                {"name": "pseudonym", "valueString": "some-pseudonym"},
                {
                    "name": "careContext",
                    "valueCoding": {
                        "system": CARE_CONTEXT_SYSTEM,
                        "code": "ImagingStudy",
                    },
                },
                {"name": "sourceType", "valueCode": "hospital"},
            ],
        },
        {
            "resourceType": "Parameters",
            "parameter": [
                {"name": "pseudonym", "valueString": "some-pseudonym"},
                {"name": "oprfKey", "valueString": "some-key"},
                {"name": "sourceType", "valueCode": "hospital"},
            ],
        },
    ],
)
def test_validate_parameters_should_raise_exception_with_missing_required_params(
    data: Dict[str, Any],
) -> None:
    with pytest.raises(ValueError):
        Parameters.model_validate(data)


def test_get_org_lokalisatie_dto_should_succeed(
    pseudonym_param: PseudonymParamter,
    oprf_key_param: OprfKeyParameter,
    care_context_param: CareContextParameter,
    source_type_param: SourceTypeParameter,
    mock_parameter: Parameters,
) -> None:
    expected = OrganizationLocalizationDto(
        oprf_jwe=pseudonym_param.value_string,
        oprf_key=oprf_key_param.value_string,
        data_domain=care_context_param.value_coding.code,
        org_types=[source_type_param.value_code],
    )

    actual = mock_parameter.get_org_lokalization_dto()

    assert expected == actual


def test_get_org_lokalisatie_dto_should_raise_exception_when_required_params_missing(
    mock_parameter: Parameters,
) -> None:
    mock_parameter.parameter.pop(0)
    with pytest.raises(ValueError):
        mock_parameter.get_org_lokalization_dto()
