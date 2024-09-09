from unittest import TestCase

from pyparsing import empty

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
        # act
        db_connection_valid = self.db.is_healthy()

        # assert
        self.assertEqual(db_connection_valid, True)

    def test_get_referral_by_domain_and_name(self) -> None:
        # arrange
        mock_referral = ReferralEntry(
            ura_number=UraNumber("12345"),
            pseudonym=Pseudonym("6d87d96a-cb78-4f5c-823b-578095da2c4a"),
            data_domain=DataDomain.BeeldBank
        )

        # act
        self.referral_service.add_one_referral(
            pseudonym=mock_referral.pseudonym,
            data_domain=mock_referral.data_domain,
            ura_number=mock_referral.ura_number,
        )
        actual_referrals = self.referral_service.get_referrals_by_domain_and_pseudonym(
            pseudonym=mock_referral.pseudonym, data_domain=mock_referral.data_domain
        )

        # assert
        for referral in actual_referrals:
            self.assertEqual(referral.ura_number, mock_referral.ura_number)
            self.assertEqual(referral.pseudonym, mock_referral.pseudonym)
            self.assertEqual(referral.data_domain, mock_referral.data_domain)

    def test_delete_referral(self) -> None:
        # arrange
        mock_referral = ReferralEntry(
            ura_number=UraNumber("12345"),
            pseudonym=Pseudonym("6d87d96a-cb78-4f5c-823b-578095da2c4a"),
            data_domain=DataDomain.BeeldBank
        )

        # act
        self.referral_service.add_one_referral(
            pseudonym=mock_referral.pseudonym,
            data_domain=mock_referral.data_domain,
            ura_number=mock_referral.ura_number,
        )
        actual_referrals = self.referral_service.get_referrals_by_domain_and_pseudonym(
            pseudonym=mock_referral.pseudonym, data_domain=mock_referral.data_domain
        )

        # assert
        for referral in actual_referrals:
            self.assertEqual(referral.ura_number, mock_referral.ura_number)
            self.assertEqual(referral.pseudonym, mock_referral.pseudonym)
            self.assertEqual(referral.data_domain, mock_referral.data_domain)

        deleted = self.referral_service.delete_one_referral(
            pseudonym=mock_referral.pseudonym, data_domain=mock_referral.data_domain, ura_number=mock_referral.ura_number
        )

        # assert
        assert deleted
        assert self.referral_service.get_referrals_by_domain_and_pseudonym(
            pseudonym=mock_referral.pseudonym, data_domain=mock_referral.data_domain
        ) == []
