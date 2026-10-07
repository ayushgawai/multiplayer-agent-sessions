"""Event bus: Redis pub/sub when REDIS_URL is set, otherwise in-process fan-out."""

from __future__ import annotations

import json
import os
import threading
from collections import defaultdict
from collections.abc import Callable
from typing import Any

from app.schemas import SessionEvent

_local_subs: dict[str, list[Callable[[str], None]]] = defaultdict(list)
_local_lock = threading.Lock()


def redis_url() -> str | None:
    return os.environ.get("REDIS_URL") or None


def publish_event(session_id: str, event: SessionEvent) -> None:
    payload = event.model_dump_json()
    url = redis_url()
    if url:
        import redis

        client = redis.Redis.from_url(url, decode_responses=True)
        try:
            client.publish(f"session:{session_id}", payload)
        finally:
            client.close()
        return
    with _local_lock:
        for cb in list(_local_subs.get(session_id, [])):
            cb(payload)


def subscribe_local(session_id: str, callback: Callable[[str], None]) -> Callable[[], None]:
    """Register an in-process subscriber. Returns an unsubscribe callable."""
    with _local_lock:
        _local_subs[session_id].append(callback)

    def _unsub() -> None:
        with _local_lock:
            subs = _local_subs.get(session_id, [])
            if callback in subs:
                subs.remove(callback)

    return _unsub


def redis_listen(session_id: str, on_message: Callable[[dict[str, Any]], None], stop: threading.Event) -> None:
    """Blocking Redis subscribe loop (run in a worker thread)."""
    url = redis_url()
    if not url:
        return
    import redis

    client = redis.Redis.from_url(url, decode_responses=True)
    pubsub = client.pubsub(ignore_subscribe_messages=True)
    pubsub.subscribe(f"session:{session_id}")
    try:
        while not stop.is_set():
            message = pubsub.get_message(timeout=0.5)
            if message and message.get("type") == "message":
                data = json.loads(message["data"])
                on_message(data)
    finally:
        pubsub.close()
        client.close()
