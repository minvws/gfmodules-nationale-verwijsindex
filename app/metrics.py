from enum import StrEnum

from opentelemetry.metrics import MeterProvider

from app.models.ura import UraNumber


class Operation(StrEnum):
    REGISTRATION = "registration"
    DELETION = "deletion"
    LOCALIZATION = "localization"


class UsageMetrics:
    def __init__(self, meter_provider: MeterProvider) -> None:
        meter = meter_provider.get_meter("nationale-verwijsindex")
        self._operations = meter.create_counter(
            "nvi_operations",
            unit="{operation}",
            description="Successful registrations, deletions and localizations per URA",
        )
        self._localization_referrals = meter.create_histogram(
            "nvi_localization_referrals",
            unit="{referral}",
            description="Number of referrals found per localization",
            explicit_bucket_boundaries_advisory=[*range(11), 20, 50],
        )

    def registered(self, ura: UraNumber) -> None:
        self._count(Operation.REGISTRATION, ura, 1)

    def deleted(self, ura: UraNumber, count: int) -> None:
        self._count(Operation.DELETION, ura, count)

    def localized(self, ura: UraNumber, referral_count: int) -> None:
        self._count(Operation.LOCALIZATION, ura, 1)
        self._localization_referrals.record(referral_count)

    def _count(self, operation: Operation, ura: UraNumber, amount: int) -> None:
        self._operations.add(amount, {"operation": operation.value, "ura": str(ura)})
