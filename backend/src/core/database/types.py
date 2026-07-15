from typing import Protocol


class Engine(Protocol):
    async def dispose(self) -> None: ...
