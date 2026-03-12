import logging

from app.services.prs.prs_registration_service import PrsRegistrationService

logger = logging.getLogger(__name__)


class PrsRegistrationServiceMock(PrsRegistrationService):
    def __init__(self) -> None:
        pass

    def register_nvi_at_prs(self) -> None:
        logger.debug("Not registering NVI at PRS because PRS Mock is enabled")
