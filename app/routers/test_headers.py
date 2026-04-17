import logging

from fastapi import APIRouter, Request

logger = logging.getLogger(__name__)
router = APIRouter(tags=["test"], prefix="/test")


@router.get("")
def test_get(request: Request) -> None:
    print("headers: ", request.headers)
