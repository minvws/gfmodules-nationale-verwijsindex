import enum
from typing import Final, List

from app.models.fhir.value_set import Hcim2024Zibs, NviOrganizationTypes


class ReferralRequestType(str, enum.Enum):
    CREATE = "create"
    DELETE = "delete"
    QUERY = "query"


class AllowedFilesExtenions(str, enum.Enum):
    PEM = "pem"
    CRT = "crt"
    CERT = "cert"
    KEY = "key"

    @classmethod
    def from_list(cls, data: List[str]) -> List["AllowedFilesExtenions"]:
        return [cls(value) for value in data]


X509_FILE_EXTENSIONS: Final[List[AllowedFilesExtenions]] = AllowedFilesExtenions.from_list(["pem", "crt", "cert"])

HCIM_2024_ZIBS = [
    Hcim2024Zibs(code=item[0], display=item[1], definition=item[2] if len(item) > 2 else None)
    for item in [
        (
            "MedicationAgreement",
            "Medicatieafspraak",
            "Een medicatieafspraak is de afspraak tussen een zorgverlener en een patiënt over het gebruik van een geneesmiddel.",
        ),
        (
            "LaboratoryTestResult",
            "Laboratorium uitslag",
            "De uitslag van een laboratorium onderzoek.",
        ),
        ("Encounter", "Contact", "Een contact tussen een patiënt en een zorgverlener."),
        (
            "Procedure",
            "Verrichting",
            "Een verrichting of behandeling die uitgevoerd is.",
        ),
        ("Condition", "Probleem", "Een gezondheidsprobleem, diagnose of aandoening."),
        (
            "AllergyIntolerance",
            "Allergie/Intolerantie",
            "Een allergie of intolerantie voor een stof.",
        ),
        (
            "ImagingStudy",
            "Beeldvormend onderzoek",
            "Een onderzoek waarbij gebruik wordt gemaakt van beeldvormende technieken.",
        ),
    ]
]

NVI_ORGANIZATION_TYPES = [
    NviOrganizationTypes(code=item[0], display=item[1])
    for item in [
        ("zbc", "Zelfstandig behandelcentrum"),
        ("huisarts", "Huisartspraktijk"),
        ("apotheek", "Apotheek"),
        ("ziekenhuis", "Ziekenhuis"),
        ("umc", "Universitair medisch centrum"),
        ("ggz", "GGZ instelling"),
        ("verpleeghuis", "Verpleeghuis"),
        ("diagnostisch-centrum", "Diagnostisch centrum"),
        ("trombosedienst", "Trombosedienst"),
        ("laboratorium", "Laboratorium"),
    ]
]
