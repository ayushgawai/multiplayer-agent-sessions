"""HTTP routes for the session service."""

from __future__ import annotations

import asyncio
import json
import queue
import threading

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect

from app.bus import redis_listen, redis_url, subscribe_local
from app.replay import replay_to_seq
from app.schemas import (
    AppendEventResponse,
    CreateSessionRequest,
    CreateSessionResponse,
    EventsPage,
    JoinSessionRequest,
    JoinSessionResponse,
    RollbackRequest,
    RollbackResponse,
    SessionEventCreate,
)
from app.store import get_store

router = APIRouter(prefix="/v1")


@router.post("/sessions", response_model=CreateSessionResponse)
def create_session(body: CreateSessionRequest) -> CreateSessionResponse:
    session = get_store().create_session(body.title, body.scenario_id)
    return CreateSessionResponse(session_id=session.session_id, join_code=session.join_code)


@router.post("/sessions/{session_id}/join", response_model=JoinSessionResponse)
def join_session(session_id: str, body: JoinSessionRequest) -> JoinSessionResponse:
    store = get_store()
    try:
        participant = store.join(
            session_id, body.join_code, body.display_name, body.role
        )
        events = store.all_events(session_id)
        snapshot = replay_to_seq(events)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="session not found") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return JoinSessionResponse(
        participant_id=participant.participant_id,
        snapshot=snapshot,
        catchup_summary=None,
    )


@router.get("/sessions/{session_id}/events", response_model=EventsPage)
def list_events(
    session_id: str,
    since: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> EventsPage:
    try:
        events, next_seq = get_store().events_since(session_id, since, limit)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="session not found") from exc
    return EventsPage(events=events, next_seq=next_seq)


@router.post("/sessions/{session_id}/events", response_model=AppendEventResponse)
def append_event(session_id: str, body: SessionEventCreate) -> AppendEventResponse:
    try:
        event = get_store().append_event(session_id, body)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="session not found") from exc
    assert event.seq is not None
    return AppendEventResponse(event_id=event.event_id, seq=event.seq)


@router.post("/sessions/{session_id}/rollback", response_model=RollbackResponse)
def rollback(session_id: str, body: RollbackRequest) -> RollbackResponse:
    store = get_store()
    try:
        snapshot, rolled = store.rollback(session_id, body.to_seq)
        events = store.all_events(session_id)
        snapshot = {**snapshot, **replay_to_seq(events, to_seq=body.to_seq)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="session not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RollbackResponse(snapshot=snapshot, rolled_back_events=rolled)


@router.websocket("/sessions/{session_id}/stream")
async def stream_events(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()
    try:
        get_store().get(session_id)
    except KeyError:
        await websocket.close(code=4404)
        return

    q: queue.Queue[str | None] = queue.Queue()
    stop = threading.Event()

    def _push(payload: str) -> None:
        q.put(payload)

    unsub = subscribe_local(session_id, _push)
    if redis_url():

        def _on_redis(data: dict) -> None:
            q.put(json.dumps(data))

        threading.Thread(
            target=redis_listen,
            args=(session_id, _on_redis, stop),
            daemon=True,
        ).start()

    try:
        while True:
            try:
                while True:
                    msg = q.get_nowait()
                    if msg is None:
                        return
                    await websocket.send_text(msg)
            except queue.Empty:
                pass
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=0.5)
            except asyncio.TimeoutError:
                continue
            except WebSocketDisconnect:
                return
    finally:
        stop.set()
        unsub()
