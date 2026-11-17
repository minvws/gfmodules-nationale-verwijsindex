from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db.db import Database
from app.db.models.organization import OrganizationEntity


def test_organizations_live_in_admin_schema(database: Database) -> None:
    with Session(database.engine) as session:
        session.add(OrganizationEntity(id=uuid4(), external_id="10000123", deleted_at=datetime.now(UTC)))
        session.commit()

        actual = session.scalars(select(OrganizationEntity).where(OrganizationEntity.external_id == "10000123")).one()
        in_admin_schema = session.scalar(
            text("SELECT count(*) FROM admin.organizations WHERE external_id = '10000123'")
        )

    assert actual.deleted_at is not None
    assert in_admin_schema == 1
