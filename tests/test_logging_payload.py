from app.data import UraNumber
from app.referral_request_payload import ReferralLoggingPayload
from app.referral_request_type import ReferralRequestType

TESTING_URA = UraNumber(123)


def test_create():
    logging_payload = ReferralLoggingPayload(
        endpoint="https://test",
        requesting_uzi_number="123",
        ura_number=TESTING_URA,
        request_type=ReferralRequestType.CREATE,
        payload={},
    )

    assert logging_payload.requesting_uzi_number == "123"
