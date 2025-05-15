import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


# DataDomain definitions
class DataDomain(Enum):
    Unknown = "unknown"
    ImagingStudy = "beeldbank"
    MedicationStatement = "medicatie verklaring"
    CarePlan = "zorgplan"

    @classmethod
    def from_str(cls, label: str) -> Optional["DataDomain"]:
        try:
            return cls(label.lower())
        except ValueError:
            return None

    @classmethod
    def from_fhir(cls, label: str) -> Optional["DataDomain"]:
        match label:
            case "ImagingStudy":
                return DataDomain.ImagingStudy
            case "MedicationStatement":
                return DataDomain.MedicationStatement
            case "CarePlan":
                return DataDomain.CarePlan
            case _:
                return None

    def to_fhir(self) -> str:
        match self:
            case DataDomain.ImagingStudy:
                return "ImagingStudy"
            case DataDomain.MedicationStatement:
                return "MedicationStatement"
            case DataDomain.CarePlan:
                return "CarePlan"
            case _:
                return ""

    def __str__(self) -> str:
        return self.value


@dataclass
class UraNumber:
    def __init__(self, value: Any) -> None:
        if (isinstance(value, int) or isinstance(value, str)) and len(str(value)) <= 8 and str(value).isdigit():
            self.value = str(value).zfill(8)
        else:
            # See https://www.zorgcsp.nl/documents/10-01-2025%20RK1%20CPS%20UZI-register%20V11.9%20NL.pdf
            raise ValueError("URA number must be 8 digits or less")

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"UraNumber({self.value})"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, UraNumber):
            return self.value == other.value
        return False


@dataclass
class Pseudonym:
    def __init__(self, value: Any) -> None:
        self.value = uuid.UUID(str(value))

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"Pseudonym({self.value})"
