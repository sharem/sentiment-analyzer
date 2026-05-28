"""RedisStreamBroker — MessageBroker adapter backed by Redis Streams + consumer groups."""

import json
import logging
import os
import socket
from collections.abc import Iterator

import redis

from backend.application.ports.message_broker import BrokerError, MessageBroker

logger = logging.getLogger(__name__)

_DEFAULT_GROUP = "sentiment-analyzer"
_DEFAULT_MAX_LEN = 10_000
_DEFAULT_BLOCK_MS = 5_000


class RedisStreamBroker(MessageBroker):
    """Persisted, ack-based transport. Producer XADDs; consumer XREADGROUPs and XACKs.

    Unlike Redis Pub/Sub, messages persist on the stream until acknowledged, so a
    restarting or slow consumer doesn't lose data. Multiple consumers in the same
    group share the work; messages stay in the pending entries list (PEL) until
    XACK'd, giving at-least-once delivery.
    """

    def __init__(
        self,
        client: redis.Redis,
        group: str = _DEFAULT_GROUP,
        consumer: str | None = None,
        max_len: int = _DEFAULT_MAX_LEN,
        block_ms: int = _DEFAULT_BLOCK_MS,
    ) -> None:
        self._client = client
        self._group = group
        self._consumer = consumer or f"{socket.gethostname()}-{os.getpid()}"
        self._max_len = max_len
        self._block_ms = block_ms

    def publish(self, topic: str, message: dict) -> None:
        try:
            self._client.xadd(
                topic,
                {"data": json.dumps(message)},
                maxlen=self._max_len,
                approximate=True,
            )
        except redis.RedisError as e:
            raise BrokerError(str(e)) from e

    def consume(self, topic: str) -> Iterator[dict]:
        self._ensure_group(topic)
        logger.info(
            f"Consuming '{topic}' as group='{self._group}' consumer='{self._consumer}'"
        )
        try:
            while True:
                resp = self._client.xreadgroup(
                    self._group,
                    self._consumer,
                    {topic: ">"},
                    count=1,
                    block=self._block_ms,
                )
                if not resp:
                    continue
                for _stream, entries in resp:
                    for entry_id, fields in entries:
                        payload = self._decode_payload(fields)
                        if payload is None:
                            self._client.xack(topic, self._group, entry_id)
                            continue
                        yield payload
                        self._client.xack(topic, self._group, entry_id)
        except redis.RedisError as e:
            raise BrokerError(str(e)) from e

    def close(self) -> None:
        self._client.close()
        logger.info("Redis Streams connection closed")

    def _ensure_group(self, topic: str) -> None:
        try:
            self._client.xgroup_create(topic, self._group, id="$", mkstream=True)
            logger.info(f"Created consumer group '{self._group}' on stream '{topic}'")
        except redis.ResponseError as e:
            if "BUSYGROUP" in str(e):
                return
            raise BrokerError(str(e)) from e
        except redis.RedisError as e:
            raise BrokerError(str(e)) from e

    @staticmethod
    def _decode_payload(fields: dict) -> dict | None:
        raw = fields.get("data") or fields.get(b"data")
        if raw is None:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return json.loads(raw)
