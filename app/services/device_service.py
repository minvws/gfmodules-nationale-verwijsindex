import logging
from typing import Sequence

from app.db.db import Database
from app.db.models.device import DeviceEntity
from app.db.repository.referral_repository import ReferralRepository
from app.models.ura import UraNumber

logger = logging.getLogger(__name__)


class DeviceService:
    def __init__(self, database: Database) -> None:
        self.database = database

    def get(self, ura_number: UraNumber, device_identifier: str) -> Sequence[DeviceEntity]:
        with self.database.get_db_session() as session:
            repo = session.get_repository(ReferralRepository)
            ds = repo.get_distinct_devices_by_ura_and_source_identifier(ura_number.value, device_identifier)
            return [DeviceEntity(d) for d in ds]

    def query(self, ura_number: UraNumber) -> Sequence[DeviceEntity]:
        with self.database.get_db_session() as session:
            repo = session.get_repository(ReferralRepository)
            ds = repo.get_distinct_devices_by_ura(ura_number.value)
            return [DeviceEntity(d) for d in ds]
