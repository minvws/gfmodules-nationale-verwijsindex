from app.db.models.referral import ReferralEntity
from app.db.repository.referral_repository import ReferralRepository
from app.models.fhir.resources.organization.resource import Organization
from app.services.organization import OrganizationService


def test_get_should_return_one_organization(
    organization_service: OrganizationService,
    referral_repository: ReferralRepository,
    mock_referral_entity: ReferralEntity,
    mock_org: Organization,
) -> None:
    with referral_repository.db_session:
        referral_repository.add_one(mock_referral_entity)
    expected = [mock_org]

    actual = organization_service.get(
        pseudonym=mock_referral_entity.pseudonym,
        data_domain=mock_referral_entity.data_domain,
    )

    assert expected == actual


def test_get_should_return_two_organizations(
    organization_service: OrganizationService,
    referral_repository: ReferralRepository,
    mock_referral_entity: ReferralEntity,
) -> None:
    with referral_repository.db_session:
        referral_1 = referral_repository.add_one(mock_referral_entity)
        mock_2 = ReferralEntity(
            pseudonym=mock_referral_entity.pseudonym,
            data_domain=mock_referral_entity.data_domain,
            ura_number="00000123",
            organization_type="pharmacy",
        )
        referral_2 = referral_repository.add_one(mock_2)
    expected = [
        Organization.from_referral(referral_1),
        Organization.from_referral(referral_2),
    ]

    actual = organization_service.get(
        pseudonym=mock_referral_entity.pseudonym,
        data_domain=mock_referral_entity.data_domain,
    )

    assert expected == actual


def test_get_should_return_one_org_based_on_org_type_filter(
    organization_service: OrganizationService,
    referral_repository: ReferralRepository,
    mock_referral_entity: ReferralEntity,
) -> None:
    with referral_repository.db_session:
        referral_repository.add_one(mock_referral_entity)
        mock_2 = ReferralEntity(
            pseudonym=mock_referral_entity.pseudonym,
            data_domain=mock_referral_entity.data_domain,
            ura_number="00000123",
            organization_type="pharmacy",
        )
        referral_2 = referral_repository.add_one(mock_2)
    expected = [Organization.from_referral(referral_2)]

    actual = organization_service.get(
        pseudonym=mock_referral_entity.pseudonym,
        data_domain=mock_referral_entity.data_domain,
        org_types=["pharmacy"],
    )

    assert expected == actual


def test_get_should_return_empty_list_when_no_match_found(
    organization_service: OrganizationService,
    referral_repository: ReferralRepository,
    mock_referral_entity: ReferralEntity,
) -> None:
    with referral_repository.db_session:
        referral_repository.add_one(mock_referral_entity)

    actual = organization_service.get(
        pseudonym=mock_referral_entity.pseudonym,
        data_domain=mock_referral_entity.data_domain,
        org_types=["pharmacy"],
    )

    assert actual == []
