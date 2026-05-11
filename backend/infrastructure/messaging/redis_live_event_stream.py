import asyncio
import json
from collections.abc import AsyncIterator

import redis.asyncio as aioredis

from backend.application.ports.live_stream import LiveEventStream


class RedisLiveEventStream(LiveEventStream):
    """Streams Redis pub/sub messages to SSE clients (async)."""

    def __init__(self, host: str, port: int) -> None:
        self._host = host
        self._port = port

    async def subscribe(self, channel: str) -> AsyncIterator[dict | None]:
        r = aioredis.Redis(host=self._host, port=self._port, decode_responses=True)
        pubsub = r.pubsub()
        await pubsub.subscribe(channel)
        try:
            while True:
                msg = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=20.0
                )
                yield json.loads(msg["data"]) if msg else None
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.unsubscribe(channel)
            await r.aclose()
