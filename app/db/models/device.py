class DeviceEntity:
    _id: str

    def __init__(self, id: str):
        self._id = id

    def __repr__(self) -> str:
        return self._id

    def __str__(self) -> str:
        return self._id
