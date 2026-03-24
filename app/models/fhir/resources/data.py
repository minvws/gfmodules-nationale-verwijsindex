from typing import Final

SOURCE_SYSTEM: Final[str] = "urn:oid:2.16.528.1.1007.3.3"  # NOSONAR
SOURCE_TYPE_SYSTEM: Final[str] = "https://nvi.proeftuin.gf.irealisatie.nl/fhir/CodeSystem/nvi-organization-types"
SUBJECT_SYSTEM: Final[str] = "https://nvi.proeftuin.gf.irealisatie.nl/fhir/NamingSystem/nvi-pseudonym"
CARE_CONTEXT_SYSTEM: Final[str] = "https://nvi.proeftuin.gf.irealisatie.nl/fhir/CodeSystem/care-context-type"
DEFAULT_DEVICE_IDENTIFIER: Final[str] = "default-device"

## LocalizationList Data

URA_SYSTEM: Final[str] = "http://fhir.nl/fhir/NamingSystem/ura"
URA_SYSTEM_EXTENSION: Final[str] = (
    "http://minvws.github.io/generiekefuncties-docs/StructureDefinition/nl-gf-localization-custodian"
)
PSEUDONYM_SYSTEM: Final[str] = "http://minvws.github.io/generiekefuncties-docs/NamingSystem/nvi-identifier"
DATA_DOMAIN_SYSTEM: Final[str] = "http://minvws.github.io/generiekefuncties-docs/CodeSystem/nl-gf-data-categories-cs"
EMPTY_REASON_SYSTEM: Final[str] = "http://terminology.hl7.org/CodeSystem/list-empty-reason"
DEVICE_SYSTEM: Final[str] = "urn:ietf:rfc:3986"
