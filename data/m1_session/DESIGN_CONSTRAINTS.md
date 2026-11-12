# Design constraints for `m1_session_v1`

Source: Manav, message of 2026-11-11, concerning `models/m1_catchup/bm25.py` in PR #26 (m1-a rules v1), fitted on smoke train and dev only.

`m1_session_v1` is the real M1 product-session dataset. These are the things the M1-A rules were fitted on, so the real set can avoid leaking them.

## Fitted scenario types

All 5 smoke scenarios: `feature`, `blocked_tool`, `handoff`, `arbitration`, `rollback`.

`m1_session_v1` must use different scenario types, not renamed templates. New names, numbers or people in the same templates do not count.

## Event-type shortcuts the rules assume

Worth breaking on purpose in the real set.

- Blocked is read only from `agent_step` events.
- Pending actions are read only from `instruction` events.
- Every `doc_update` and `rollback` counts as completed.
- Every `arbitration` and `interrupt` counts as a decision.
- `join` and `leave` never produce a claim.

## Phrasing cues the rules key on

Taken from smoke train and dev text.

- **Blocked:** "blocked", "blocker", "waiting on", "cannot/can't", "fails/failing", "error", "limit", "stuck".
- **Decisions:** "decided/decision", "agreed", "chose", "approve", "merged the proposals", "Do not …", "Acknowledged.", and sentences starting "Skip …", "Hold the …", "Ownership of … moves …".
- **Pending:** "will", "must", "<Name>, please …", "next step", "to do", "needs to", "follow up", "assign", "by end of".
- **In progress:** "in progress", "running", "started", "working on", "ongoing", "N of M", "N percent", "writing", "halted".
- **Completed:** "done", "completed", "finished", "merged", "resolved", "shipped", "0 failures", "passed" (only when nothing failed), and sentences starting with Created, Built, Updated, Added, Removed, Replaced, Applied or Switched.
- **No status:** "Paused" and "Pausing" are treated as no status.

## Cases to include on purpose

- Blockers reported by humans or by tool results.
- Pending actions stated by agents.
- `doc_update` events that are drafts rather than finished work.
- Decisions without the cue words above.
- Status changes later in the session that override earlier ones. M1-A does not track that.

This gives M1-A a fair, unfitted score, and leaves room for the learned candidates to show they are better.

## Rules

1. Freeze the `m1_session_v1` splits before any M1-A refit.
2. M1-A must not be refit on the real set's dev or test.
3. Collect sessions from scenario briefs. Do not script them to dodge the keywords above.
4. After collection, report how many sessions and cases fall outside the cue list.
