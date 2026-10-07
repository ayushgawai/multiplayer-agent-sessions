"""Initial sessions, participants, events tables.

Revision ID: 001_event_log
Revises:
Create Date: 2026-10-06
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_event_log"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sessions",
        sa.Column("session_id", sa.String(length=64), primary_key=True),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("join_code", sa.String(length=16), nullable=False),
        sa.Column("scenario_id", sa.String(length=64), nullable=True),
        sa.Column("next_seq", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sessions_join_code", "sessions", ["join_code"])

    op.create_table(
        "participants",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.String(length=64), sa.ForeignKey("sessions.session_id"), nullable=False),
        sa.Column("participant_id", sa.String(length=32), nullable=False),
        sa.Column("display_name", sa.String(length=128), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.UniqueConstraint("session_id", "participant_id", name="uq_session_participant"),
    )

    op.create_table(
        "events",
        sa.Column("event_id", sa.String(length=64), primary_key=True),
        sa.Column("session_id", sa.String(length=64), sa.ForeignKey("sessions.session_id"), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_kind", sa.String(length=16), nullable=False),
        sa.Column("actor_id", sa.String(length=64), nullable=False),
        sa.Column("actor_display_name", sa.String(length=128), nullable=False),
        sa.Column("actor_role", sa.String(length=32), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("parent_event", sa.String(length=64), nullable=True),
        sa.Column("root_instruction", sa.String(length=64), nullable=True),
        sa.Column("labels_json", sa.JSON(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.UniqueConstraint("session_id", "seq", name="uq_session_seq"),
    )
    op.create_index("ix_events_session_id", "events", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_events_session_id", table_name="events")
    op.drop_table("events")
    op.drop_table("participants")
    op.drop_index("ix_sessions_join_code", table_name="sessions")
    op.drop_table("sessions")
