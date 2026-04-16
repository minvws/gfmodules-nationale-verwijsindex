import enum
from typing import Final, List

from app.models.fhir.value_set import NviOrganizationTypes


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
