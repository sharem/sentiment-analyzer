from abc import ABC


class LiveEventStream(ABC):
    """Port for the SSE subscribe side — yields event dicts or None as keepalive."""

    async def subscribe(self, channel: str):
        raise NotImplementedError
