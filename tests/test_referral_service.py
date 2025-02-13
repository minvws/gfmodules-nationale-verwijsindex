from unittest import TestCase
from uuid import uuid4

from fastapi import HTTPException

from app.data import DataDomain, Pseudonym, UraNumber
from app.db.db import Database
from app.response_models.referrals import ReferralEntry
from app.services.authorization_services.stub import StubAuthService
from app.services.referral_service import ReferralService
from tests.test_config import get_test_config


class ReferralServiceTest(TestCase):
    def setUp(self) -> None:
        config = get_test_config()
        # setup db
        self.db = Database("sqlite:///:memory:", config)
        self.db.generate_tables()
        self.auth_service = StubAuthService()
        # setup service
        self.referral_service = ReferralService(self.db, authorization_service=self.auth_service)

    def test_db_connection(self) -> None:
        db_connection_valid = self.db.is_healthy()

        self.assertEqual(db_connection_valid, True)

    def test_add_referral(self) -> None:
        mock_referral = ReferralEntry(
            ura_number=UraNumber("12345"),
            pseudonym=Pseudonym("6d87d96a-cb78-4f5c-823b-578095da2c4a"),
            data_domain=DataDomain.ImagingStudy,
        )

        self.referral_service.add_one_referral(
            pseudonym=mock_referral.pseudonym,
            data_domain=mock_referral.data_domain,
            ura_number=mock_referral.ura_number,
            uzi_number="testuzinumber",
            request_url="https://test",
        )

    def test_add_referral_duplicate(self) -> None:
        mock_referral = ReferralEntry(
            ura_number=UraNumber("12345"),
            pseudonym=Pseudonym("6d87d96a-cb78-4f5c-823b-578095da2c4a"),
            data_domain=DataDomain.ImagingStudy,
        )

        with self.assertRaises(HTTPException) as context:
            for i in range(2):
                self.referral_service.add_one_referral(
                    pseudonym=mock_referral.pseudonym,
                    data_domain=mock_referral.data_domain,
                    ura_number=mock_referral.ura_number,
                    uzi_number="testuzinumber",
                    request_url="https://test",
                )
        self.assertEqual(context.exception.status_code, 409)

    def test_get_referral_by_domain_and_name(self) -> None:
        mock_referral = ReferralEntry(
            ura_number=UraNumber("12345"),
            pseudonym=Pseudonym("6d87d96a-cb78-4f5c-823b-578095da2c4a"),
            data_domain=DataDomain.ImagingStudy,
        )

        self.referral_service.add_one_referral(
            pseudonym=mock_referral.pseudonym,
            data_domain=mock_referral.data_domain,
            ura_number=mock_referral.ura_number,
            uzi_number="testuzinumber",
            request_url="https://test",
        )
        actual_referrals = self.referral_service.get_referrals_by_domain_and_pseudonym(
            pseudonym=mock_referral.pseudonym,
            data_domain=mock_referral.data_domain,
        )

        for referral in actual_referrals:
            self.assertEqual(referral.ura_number, mock_referral.ura_number)
            self.assertEqual(referral.pseudonym, mock_referral.pseudonym)
            self.assertEqual(referral.data_domain, mock_referral.data_domain)

    def test_get_referral_not_found(self) -> None:
        with self.assertRaises(HTTPException) as context:
            self.referral_service.get_referrals_by_domain_and_pseudonym(
                pseudonym=Pseudonym(str(uuid4())), data_domain=DataDomain.ImagingStudy
            )
        self.assertEqual(context.exception.status_code, 404)

    def test_delete_referral(self) -> None:
        mock_referral = ReferralEntry(
            ura_number=UraNumber("12345"),
            pseudonym=Pseudonym("6d87d96a-cb78-4f5c-823b-578095da2c4a"),
            data_domain=DataDomain.ImagingStudy,
        )

        self.referral_service.add_one_referral(
            pseudonym=mock_referral.pseudonym,
            data_domain=mock_referral.data_domain,
            ura_number=mock_referral.ura_number,
            uzi_number="testuzinumber",
            request_url="https://test",
        )
        actual_referrals = self.referral_service.get_referrals_by_domain_and_pseudonym(
            pseudonym=mock_referral.pseudonym,
            data_domain=mock_referral.data_domain,
        )

        for referral in actual_referrals:
            self.assertEqual(referral.ura_number, mock_referral.ura_number)
            self.assertEqual(referral.pseudonym, mock_referral.pseudonym)
            self.assertEqual(referral.data_domain, mock_referral.data_domain)

        self.referral_service.delete_one_referral(
            pseudonym=mock_referral.pseudonym,
            data_domain=mock_referral.data_domain,
            ura_number=mock_referral.ura_number,
            request_url="https://test",
        )

        with self.assertRaises(HTTPException) as context:
            self.referral_service.get_referrals_by_domain_and_pseudonym(
                pseudonym=mock_referral.pseudonym,
                data_domain=mock_referral.data_domain,
            )
        self.assertEqual(context.exception.status_code, 404)

    def test_delete_referral_not_found(self) -> None:
        with self.assertRaises(HTTPException) as context:
            self.referral_service.delete_one_referral(
                pseudonym=Pseudonym(str(uuid4())),
                data_domain=DataDomain.ImagingStudy,
                ura_number=UraNumber("99999"),
                request_url="https://test",
            )
        self.assertEqual(context.exception.status_code, 404)

    def test_query_referral_single_item(self) -> None:
        mock_referral = ReferralEntry(
            ura_number=UraNumber("12345"),
            pseudonym=Pseudonym("6d87d96a-cb78-4f5c-823b-578095da2c4a"),
            data_domain=DataDomain.ImagingStudy,
        )

        self.referral_service.add_one_referral(
            pseudonym=mock_referral.pseudonym,
            data_domain=mock_referral.data_domain,
            ura_number=mock_referral.ura_number,
            uzi_number="testuzinumber",
            request_url="https://test",
        )
        actual_referrals = self.referral_service.query_referrals(
            pseudonym=mock_referral.pseudonym,
            ura_number=mock_referral.ura_number,
            data_domain=None,
            request_url="http://test",
        )

        for referral in actual_referrals:
            self.assertEqual(referral.ura_number, mock_referral.ura_number)
            self.assertEqual(referral.pseudonym, mock_referral.pseudonym)
            self.assertEqual(referral.data_domain, mock_referral.data_domain)

    def test_query_referral_two_items(self) -> None:
        mock_referral = ReferralEntry(
            ura_number=UraNumber("12345"),
            pseudonym=Pseudonym("6d87d96a-cb78-4f5c-823b-578095da2c4a"),
            data_domain=DataDomain.ImagingStudy,
        )

        self.referral_service.add_one_referral(
            uzi_number="testuzi_number",
            pseudonym=mock_referral.pseudonym,
            data_domain=mock_referral.data_domain,
            ura_number=mock_referral.ura_number,
            request_url="https://test",
        )

        mock_referral_2 = ReferralEntry(
            ura_number=mock_referral.ura_number,
            pseudonym=Pseudonym("3ac6b06c-a07c-4f51-a8a6-a17143412038"),
            data_domain=mock_referral.data_domain,
        )

        self.referral_service.add_one_referral(
            pseudonym=mock_referral_2.pseudonym,
            data_domain=mock_referral_2.data_domain,
            ura_number=mock_referral_2.ura_number,
            uzi_number="testuzi_number",
            request_url="https://test",
        )

        actual_referrals = self.referral_service.query_referrals(
            pseudonym=None,
            ura_number=mock_referral.ura_number,
            data_domain=None,
            request_url="https://test",
        )

        self.assertEqual(len(actual_referrals), 2)

    def test_query_referral_not_found(self) -> None:
        with self.assertRaises(HTTPException) as context:
            _ = self.referral_service.query_referrals(
                pseudonym=Pseudonym(str(uuid4())),
                ura_number=UraNumber("99999"),
                data_domain=None,
                request_url="http://test",
            )
        self.assertEqual(context.exception.status_code, 404)

        with self.assertRaises(HTTPException) as context:
            _ = self.referral_service.query_referrals(
                pseudonym=None,
                ura_number=UraNumber("99999"),
                data_domain=DataDomain.MedicationStatement,
                request_url="http://test",
            )
        self.assertEqual(context.exception.status_code, 404)
