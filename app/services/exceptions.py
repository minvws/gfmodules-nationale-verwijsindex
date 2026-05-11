from fastapi import HTTPException


class NotFoundError(HTTPException):
    def __init__(self):
        super().__init__(status_code=404, detail="Registration not found")


class ConflictError(HTTPException):
    def __init__(self):
        super().__init__(status_code=409, detail="Registration Already Exists")
