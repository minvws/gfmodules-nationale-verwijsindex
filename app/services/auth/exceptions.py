from fastapi import HTTPException


class MissingHeaderProperty(HTTPException):
    def __init__(self, prop: str) -> None:
        super().__init__(status_code=401, detail=f"Missing required header property: {prop}")


class InvalidHeaderPropertyValue(HTTPException):
    def __init__(self, prop: str, value: str) -> None:
        super().__init__(status_code=401, detail=f"Invalid header property {prop} with value {value}")
