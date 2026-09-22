"""HTTP routes for the session service."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect

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
from app.store import store

router = APIRouter(prefix="/v1")


@router.post("/sessions", response_model=CreateSessionResponse)
def create_session(body: CreateSessionRequest) -> CreateSessionResponse:
    session = store.create_session(body.title, body.scenario_id)
    return CreateSessionResponse(session_id=session.session_id, join_code=session.join_code)


@router.post("/sessions/{session_id}/join", response_model=JoinSessionResponse)
def join_session(session_id: str, body: JoinSessionRequest) -> JoinSessionResponse:
    try:
        participant = store.join(
            session_id, body.join_code, body.display_name, body.role
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="session not found") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return JoinSessionResponse(
        participant_id=participant.participant_id,
        snapshot={"session_id": session_id, "event_count": 0},
        catchup_summary=None,
    )


@router.get("/sessions/{session_id}/events", response_model=EventsPage)
def list_events(
    session_id: str,
    since: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> EventsPage:
    try:
        events, next_seq = store.events_since(session_id, since, limit)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="session not found") from exc
    return EventsPage(events=events, next_seq=next_seq)


@router.post("/sessions/{session_id}/events", response_model=AppendEventResponse)
def append_event(session_id: str, body: SessionEventCreate) -> AppendEventResponse:
    try:
        event = store.append_event(session_id, body)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="session not found") from exc
    assert event.seq is not None
    return AppendEventResponse(event_id=event.event_id, seq=event.seq)


@router.post("/sessions/{session_id}/rollback", response_model=RollbackResponse)
def rollback(session_id: str, body: RollbackRequest) -> RollbackResponse:
    try:
        snapshot, rolled = store.rollback(session_id, body.to_seq)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="session not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RollbackResponse(snapshot=snapshot, rolled_back_events=rolled)


@router.websocket("/sessions/{session_id}/stream")
async def stream_events(websocket: WebSocket, session_id: str) -> None:
    """Stub fan-out: accept connection and close cleanly. Redis pub/sub later."""
    await websocket.accept()
    try:
        store.get(session_id)
    except KeyError:
        await websocket.close(code=4404)
        return
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        return
