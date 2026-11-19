from uuid import UUID

from sqlalchemy import ColumnElement, ScalarSelect, and_, select

from app.db.decorator import repository
from app.db.models.organization import OrganizationEntity
from app.db.repository.respository_base import RepositoryBase


def _active_with(ura_number: str) -> ColumnElement[bool]:
    """
    The active organization with the URA number. Only one active organization can carry a URA number.
    """
    return and_(OrganizationEntity.external_id == ura_number, OrganizationEntity.deleted_at.is_(None))


def active_organization_id(ura_number: str) -> ScalarSelect[UUID]:
    return select(OrganizationEntity.id).where(_active_with(ura_number)).scalar_subquery()


@repository(OrganizationEntity)
class OrganizationRepository(RepositoryBase):
    def find_active(self, ura_number: str) -> OrganizationEntity | None:
        """
        Locks the organization row (FOR SHARE) until the transaction ends, so it cannot be deleted while a referral is
        being linked to it.
        """
        stmt = select(OrganizationEntity).where(_active_with(ura_number)).with_for_update(read=True)
        return self.db_session.execute(stmt).scalars().first()
