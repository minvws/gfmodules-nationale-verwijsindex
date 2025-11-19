import abc

from app.models.referrals.logging import ReferralLoggingPayload


class ReferralRequestLogger(abc.ABC):
    @abc.abstractmethod
    def log(self, referral: ReferralLoggingPayload) -> None: ...

    @abc.abstractmethod
    def log_query(self, referral: ReferralLoggingPayload) -> None: ...
