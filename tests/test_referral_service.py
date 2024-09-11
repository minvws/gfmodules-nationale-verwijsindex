from unittest import TestCase
from uuid import uuid4

from fastapi import HTTPException

from app.config import set_config
from app.data import UraNumber, Pseudonym, DataDomain
from app.response_models.referrals import ReferralEntry
from app.services.referral_service import ReferralService
from app.db.db import Database
from test_config import get_test_config


class ReferralServiceTest(TestCase):

    def setUp(self) -> None:
        set_config(get_test_config())
        # setup db
        self.db = Database("sqlite:///:memory:")
        self.db.generate_tables()
        # setup service
        self.referral_service = ReferralService(self.db)

    def test_db_connection(self) -> None:
        db_connection_valid = self.db.is_healthy()

        self.assertEqual(db_connection_valid, True)

    def test_add_referral(self) -> None:
        mock_referral = ReferralEntry(
            ura_number=UraNumber("12345"),
            pseudonym=Pseudonym("6d87d96a-cb78-4f5c-823b-578095da2c4a"),
            data_domain=DataDomain.BeeldBank
        )

        self.referral_service.add_one_referral(
            pseudonym=mock_referral.pseudonym,
            data_domain=mock_referral.data_domain,
            ura_number=mock_referral.ura_number,
        )

    def test_add_referral_duplicate(self) -> None:
        mock_referral = ReferralEntry(
            ura_number=UraNumber("12345"),
            pseudonym=Pseudonym("6d87d96a-cb78-4f5c-823b-578095da2c4a"),
            data_domain=DataDomain.BeeldBank
        )

        with self.assertRaises(HTTPException) as context:
            for i in range(2):
                self.referral_service.add_one_referral(
                    pseudonym=mock_referral.pseudonym,
                    data_domain=mock_referral.data_domain,
                    ura_number=mock_referral.ura_number,
                )
        self.assertEqual(context.exception.status_code, 409)


    def test_get_referral_by_domain_and_name(self) -> None:
        mock_referral = ReferralEntry(
            ura_number=UraNumber("12345"),
            pseudonym=Pseudonym("6d87d96a-cb78-4f5c-823b-578095da2c4a"),
            data_domain=DataDomain.BeeldBank
        )

        self.referral_service.add_one_referral(
            pseudonym=mock_referral.pseudonym,
            data_domain=mock_referral.data_domain,
            ura_number=mock_referral.ura_number,
        )
        actual_referrals = self.referral_service.get_referrals_by_domain_and_pseudonym(
            pseudonym=mock_referral.pseudonym, data_domain=mock_referral.data_domain
        )

        for referral in actual_referrals:
            self.assertEqual(referral.ura_number, mock_referral.ura_number)
            self.assertEqual(referral.pseudonym, mock_referral.pseudonym)
            self.assertEqual(referral.data_domain, mock_referral.data_domain)

    def test_get_referral_not_found(self) -> None:
        with self.assertRaises(HTTPException) as context:
            self.referral_service.get_referrals_by_domain_and_pseudonym(
                pseudonym=Pseudonym(str(uuid4())), data_domain=DataDomain.BeeldBank
            )
        self.assertEqual(context.exception.status_code, 404)

    def test_delete_referral(self) -> None:
        mock_referral = ReferralEntry(
            ura_number=UraNumber("12345"),
            pseudonym=Pseudonym("6d87d96a-cb78-4f5c-823b-578095da2c4a"),
            data_domain=DataDomain.BeeldBank
        )

        self.referral_service.add_one_referral(
            pseudonym=mock_referral.pseudonym,
            data_domain=mock_referral.data_domain,
            ura_number=mock_referral.ura_number,
        )
        actual_referrals = self.referral_service.get_referrals_by_domain_and_pseudonym(
            pseudonym=mock_referral.pseudonym, data_domain=mock_referral.data_domain
        )

        for referral in actual_referrals:
            self.assertEqual(referral.ura_number, mock_referral.ura_number)
            self.assertEqual(referral.pseudonym, mock_referral.pseudonym)
            self.assertEqual(referral.data_domain, mock_referral.data_domain)

        self.referral_service.delete_one_referral(
            pseudonym=mock_referral.pseudonym, data_domain=mock_referral.data_domain, ura_number=mock_referral.ura_number
        )

        with self.assertRaises(HTTPException) as context:
            self.referral_service.get_referrals_by_domain_and_pseudonym(
                pseudonym=mock_referral.pseudonym, data_domain=mock_referral.data_domain
            )
        self.assertEqual(context.exception.status_code, 404)

    def test_delete_referral_not_found(self) -> None:
        with self.assertRaises(HTTPException) as context:
            self.referral_service.delete_one_referral(
                pseudonym=Pseudonym(str(uuid4())),
                data_domain=DataDomain.BeeldBank,
                ura_number=UraNumber("99999")
            )
        self.assertEqual(context.exception.status_code, 404)

    def test_query_referral_single_item(self) -> None:
        mock_referral = ReferralEntry(
            ura_number=UraNumber("12345"),
            pseudonym=Pseudonym("6d87d96a-cb78-4f5c-823b-578095da2c4a"),
            data_domain=DataDomain.BeeldBank
        )

        self.referral_service.add_one_referral(
            pseudonym=mock_referral.pseudonym,
            data_domain=mock_referral.data_domain,
            ura_number=mock_referral.ura_number,
        )
        actual_referrals = self.referral_service.query_referrals(
            pseudonym=mock_referral.pseudonym, ura_number=mock_referral.ura_number, data_domain=None
        )

        for referral in actual_referrals:
            self.assertEqual(referral.ura_number, mock_referral.ura_number)
            self.assertEqual(referral.pseudonym, mock_referral.pseudonym)
            self.assertEqual(referral.data_domain, mock_referral.data_domain)

    def test_query_referral_two_items(self) -> None:
        mock_referral = ReferralEntry(
            ura_number=UraNumber("12345"),
            pseudonym=Pseudonym("6d87d96a-cb78-4f5c-823b-578095da2c4a"),
            data_domain=DataDomain.BeeldBank
        )

        self.referral_service.add_one_referral(
            pseudonym=mock_referral.pseudonym,
            data_domain=mock_referral.data_domain,
            ura_number=mock_referral.ura_number,
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
        )

        actual_referrals = self.referral_service.query_referrals(
            pseudonym=None, ura_number=mock_referral.ura_number, data_domain=None
        )

        self.assertEqual(len(actual_referrals), 2)

    def test_query_referral_not_found(self) -> None:
        with self.assertRaises(HTTPException) as context:
            _ = self.referral_service.query_referrals(
                pseudonym=Pseudonym(str(uuid4())), ura_number=UraNumber("99999"), data_domain=None
            )
        self.assertEqual(context.exception.status_code, 404)

        with self.assertRaises(HTTPException) as context:
            _ = self.referral_service.query_referrals(
                pseudonym=None, ura_number=UraNumber("99999"), data_domain=DataDomain.Medicatie
            )
        self.assertEqual(context.exception.status_code, 404)
