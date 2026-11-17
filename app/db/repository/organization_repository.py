from uuid import UUID

from sqlalchemy import ScalarSelect, select

from app.db.decorator import repository
from app.db.models.organization import OrganizationEntity
from app.db.repository.respository_base import RepositoryBase


def active_organization_id(ura_number: str) -> ScalarSelect[UUID]:
    """
    Id of the active organization with the URA number. Only one active organization can carry a URA number.
    """
    return (
        select(OrganizationEntity.id)
        .where(OrganizationEntity.external_id == ura_number, OrganizationEntity.deleted_at.is_(None))
        .scalar_subquery()
    )


@repository(OrganizationEntity)
class OrganizationRepository(RepositoryBase):
    def find_active(self, ura_number: str) -> OrganizationEntity | None:
        stmt = select(OrganizationEntity).where(OrganizationEntity.id == active_organization_id(ura_number))
        return self.db_session.execute(stmt).scalars().first()
