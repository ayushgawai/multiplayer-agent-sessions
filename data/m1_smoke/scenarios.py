# ruff: noqa: E501
"""Hand-authored scenario templates for the M1 smoke dataset.

Each template is a fixed list of events. ``instantiate`` fills the placeholders from a
``random.Random`` passed in by the generator, so output depends only on the seed.

Event fields:
  type   session event type (see schema.EVENT_TYPES)
  who    role key (h1, h2 humans; a1, a2 agents) or None for a system event
  text   event text with {placeholders}
  label  gold status of the item this event settles: completed, in_progress, blocked,
         decision, pending_action, or None for a neutral event
  claim  gold summary sentence for a labelled event
  fact   optional short critical fact for the same claim
  also   relative offsets (negative ints) of extra supporting events for claim and fact
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

# Distinct from the wire names so templates read naturally.
HUMANS = ("Maya", "Ravi", "Chen", "Lena", "Omar", "Sofia", "Tariq", "Nina")
AGENTS = ("Atlas", "Beacon", "Cobalt", "Delta", "Ember", "Flint")

GENERIC_QUERIES = (
    "Catch me up on what happened while I was away.",
    "What is done, what is stuck, and what do I need to do?",
    "Summarize the session so far for someone joining now.",
)


@dataclass(frozen=True)
class E:
    type: str
    who: str | None
    text: str
    label: str | None = None
    claim: str | None = None
    fact: str | None = None
    also: tuple[int, ...] = ()


@dataclass(frozen=True)
class Scenario:
    key: str
    events: tuple[E, ...]
    pools: tuple[tuple[str, ...], ...]  # each row is one parameter choice (see keys)
    keys: tuple[str, ...]
    ranges: tuple[tuple[str, int, int], ...] = ()


# --- Template 1: a human and two agents implement a feature -------------------------------
FEATURE = Scenario(
    key="feature",
    keys=("feature", "module", "slug", "fmt", "db"),
    pools=(
        ("CSV export", "exporter", "csv_export", "CSV", "reports"),
        ("PDF export", "exporter", "pdf_export", "PDF", "archive"),
        ("audit log view", "viewer", "audit_view", "JSON", "audit"),
        ("tag filter", "search", "tag_filter", "YAML", "catalog"),
    ),
    ranges=(("n", 4, 9), ("k", 3, 8), ("pr", 40, 99)),
    events=(
        E("instruction", "h1", "Please add {feature} to the {module} module today. {a1} builds it and {a2} writes the tests."),
        E("agent_step", "a1", "Plan: add {module}/{slug}.py, hook it into the session menu, then hand tests to {a2}."),
        E("tool_call", "a1", "doc_read {module}/__init__.py to find the registration point."),
        E("tool_result", "a1", "Found the REGISTRY list in {module}/__init__.py at line 41."),
        E("doc_update", "a1", "Created {module}/{slug}.py with the {slug} handler and registered it in REGISTRY.",
          "completed", "{a1} implemented the {feature} handler and registered it in the {module} module.",
          "{feature} handler is registered in REGISTRY"),
        E("instruction", "h2", "Use the existing {fmt} serializer. Do not write a new one.",
          "decision", "{h2} decided {feature} must reuse the existing {fmt} serializer instead of a new one.",
          "reuse the existing {fmt} serializer"),
        E("agent_step", "a1", "Switched {slug}.py to the shared {fmt} serializer and removed 38 lines of duplicate code.",
          "completed", "{a1} switched {slug}.py to the shared {fmt} serializer and removed 38 duplicate lines."),
        E("handoff", "a1", "Handing over to {a2}: the handler is ready, please write tests in tests/test_{slug}.py."),
        E("agent_step", "a2", "Writing {n} tests for {slug}: empty input, unicode text, and large payloads.",
          "in_progress", "{a2} is writing {n} tests for {slug} covering empty input, unicode text, and large payloads.",
          "{a2} is writing {n} tests for {slug}"),
        E("tool_call", "a2", "run pytest tests/test_{slug}.py"),
        E("tool_result", "a2", "{k} passed, 1 failed: test_large_payload exceeds the 2 s timeout."),
        E("agent_step", "a2", "test_large_payload needs the {db} fixture, which only {h1} can provision. I cannot continue that test.",
          "blocked", "{a2} is blocked on test_large_payload because only {h1} can provision the {db} fixture.",
          "test_large_payload is blocked on the {db} fixture", (-1,)),
        E("instruction", "h1", "I will provision the {db} fixture tomorrow morning.",
          "pending_action", "{h1} will provision the {db} fixture tomorrow morning.",
          "{h1} provisions the {db} fixture tomorrow morning"),
        E("instruction", "h2", "Someone must update the changelog before the release.",
          "pending_action", "The changelog must be updated before the release."),
        E("agent_step", "a1", "Opened review request #{pr} for {slug}.py."),
        E("doc_update", "a1", "Updated docs/{module}.md with a usage example for {feature}.",
          "completed", "{a1} added a {feature} usage example to docs/{module}.md."),
    ),
)

# --- Template 2: an agent blocked on a failed tool call -----------------------------------
BLOCKED_TOOL = Scenario(
    key="blocked_tool",
    keys=("source", "metric", "report"),
    pools=(
        ("the finance dashboard", "revenue", "board report"),
        ("the usage warehouse", "weekly active users", "growth memo"),
        ("the support desk export", "ticket backlog", "support review"),
    ),
    ranges=(("rows", 800, 2400),),
    events=(
        E("instruction", "h1", "Compile the {metric} table for the {report} from {source}."),
        E("agent_step", "a1", "Plan: pull the data, build the table with table_build, then draft the summary paragraph."),
        E("tool_call", "a1", "web_search {metric} definitions used by {source}"),
        E("tool_result", "a1", "Found 3 usable references describing how {source} computes {metric}."),
        E("tool_call", "a1", "doc_read export.csv from {source}"),
        E("tool_result", "a1", "Read {rows} rows from export.csv."),
        E("agent_step", "a1", "Built the {metric} table with {rows} rows and 6 columns.",
          "completed", "{a1} built the {metric} table with {rows} rows and 6 columns.",
          "the {metric} table has {rows} rows"),
        E("tool_call", "a1", "calc quarterly growth rate for {metric}"),
        E("tool_result", "a1", "Error: calc timed out after 10 s on the quarter 3 input."),
        E("agent_step", "a1", "I retried calc with a smaller window and hit the same timeout. I am blocked on the quarterly growth numbers.",
          "blocked", "{a1} is blocked on the quarterly growth numbers because calc times out on quarter 3.",
          "quarterly growth is blocked by a calc timeout", (-1,)),
        E("instruction", "h2", "Skip the quarterly growth numbers for now. Use annual figures only.",
          "decision", "{h2} decided to use annual figures only and skip the quarterly growth numbers.",
          "use annual figures only"),
        E("agent_step", "a1", "Drafting the summary paragraph from the annual figures."),
        E("interrupt", "h1", "Stop. Do not publish anything until legal reviews the {report} wording.",
          "decision", "{h1} put publication of the {report} on hold until legal reviews the wording.",
          "publication is on hold until legal review"),
        E("agent_step", "a1", "Halted. Draft saved as draft_v1 with the summary paragraph about 80 percent done.",
          "in_progress", "The {report} draft is saved as draft_v1 with the summary about 80 percent done.",
          "draft_v1 is about 80 percent done"),
        E("instruction", "h2", "{h1}, please send the draft to legal tomorrow.",
          "pending_action", "{h1} must send the {report} draft to legal tomorrow.",
          "{h1} sends the draft to legal tomorrow"),
    ),
)

# --- Template 3: a handoff between humans -------------------------------------------------
HANDOFF = Scenario(
    key="handoff",
    keys=("area", "deadline"),
    pools=(
        ("billing page", "Friday"),
        ("onboarding flow", "Thursday"),
        ("settings page", "Monday"),
    ),
    ranges=(("tokens", 1, 3), ("snaps", 9, 24)),
    events=(
        E("instruction", "h1", "{a1}, redesign the {area} header and keep the existing copy."),
        E("agent_step", "a1", "Reading the current {area} layout and header components."),
        E("doc_update", "a1", "Replaced the {area} header with the two-column layout.",
          "completed", "{a1} replaced the {area} header with the two-column layout.",
          "the {area} header uses the two-column layout"),
        E("instruction", "h1", "Good. Also add a dark mode variant."),
        E("agent_step", "a1", "Started the dark mode variant, {tokens} of 5 color tokens mapped.",
          "in_progress", "{a1} is building the dark mode variant, with {tokens} of 5 color tokens mapped.",
          "dark mode has {tokens} of 5 color tokens mapped"),
        E("instruction", "h1", "I am out from tomorrow. {h2} takes over the {area}."),
        E("handoff", "h1", "Ownership of the {area} moves from {h1} to {h2}.",
          "decision", "Ownership of the {area} moved from {h1} to {h2}.",
          "{h2} now owns the {area}"),
        E("instruction", "h2", "Acknowledged. Ship the redesign by {deadline}. Dark mode can follow later.",
          "decision", "{h2} set a {deadline} deadline for the redesign and deferred dark mode.",
          "ship the redesign by {deadline}"),
        E("agent_step", "a1", "Pausing dark mode as requested. Token mapping is saved at {tokens} of 5."),
        E("tool_call", "a1", "run the visual regression suite for the {area}"),
        E("tool_result", "a1", "Visual regression: {snaps} snapshots updated, 0 failures.",
          "completed", "Visual regression for the {area} passed with {snaps} updated snapshots and no failures."),
        E("instruction", "h2", "{a1}, I need the legal footer text before we ship."),
        E("agent_step", "a1", "The legal footer text is missing from the repo and I cannot ship without it.",
          "blocked", "Shipping the {area} is blocked because the legal footer text is missing.",
          "the legal footer text is missing"),
        E("instruction", "h2", "I will email legal for the footer text today.",
          "pending_action", "{h2} will email legal for the footer text today.",
          "{h2} emails legal for the footer text"),
        E("agent_step", "a1", "Prepared a placeholder footer so layout review can proceed."),
    ),
)

# --- Template 4: an arbitration decision between two agents -------------------------------
ARBITRATION = Scenario(
    key="arbitration",
    keys=("cfg", "limit"),
    pools=(
        ("config/retry.yaml", "50"),
        ("config/upload.yaml", "40"),
        ("config/sync.yaml", "60"),
    ),
    ranges=(("retries", 4, 6), ("soak", 20, 45)),
    events=(
        E("instruction", "h1", "{a1} and {a2}, tune the retry policy in {cfg}. I want fewer failed uploads."),
        E("agent_step", "a1", "Proposal A: raise max_retries from 3 to 8 with a fixed 2 s backoff."),
        E("agent_step", "a2", "Proposal B: keep max_retries at 3 and switch to exponential backoff starting at 1 s."),
        E("tool_call", "a1", "doc_write {cfg} max_retries: 8"),
        E("tool_call", "a2", "doc_write {cfg} backoff: exponential"),
        E("tool_result", "a1", "Write conflict on {cfg}: {a2} wrote the same block 120 ms earlier."),
        E("arbitration", None, "Conflict on {cfg}: accept A, accept B, merge, or escalate. Selected: merge with max_retries {retries} and exponential backoff from 1 s.",
          "decision", "Arbitration merged both proposals in {cfg}: max_retries {retries} with exponential backoff from 1 s.",
          "arbitration merged the proposals with max_retries {retries}"),
        E("doc_update", "a1", "Applied the merged retry policy to {cfg}.",
          "completed", "{a1} applied the merged retry policy to {cfg}."),
        E("agent_step", "a2", "Running the upload soak test with the merged policy, {soak} of 100 runs done.",
          "in_progress", "{a2} is running the upload soak test, with {soak} of 100 runs done.",
          "the soak test is at {soak} of 100 runs"),
        E("tool_result", "a2", "Soak test: 3 failures in {soak} runs, all from the staging proxy timing out."),
        E("agent_step", "a2", "The staging proxy times out above 20 requests per second, so the soak test cannot finish until the limit is raised.",
          "blocked", "The soak test is blocked because the staging proxy times out above 20 requests per second.",
          "the soak test is blocked by the staging proxy limit", (-1,)),
        E("instruction", "h1", "Approved: keep the merged retry policy.",
          "decision", "{h1} approved keeping the merged retry policy."),
        E("instruction", "h1", "{h2}, please raise the staging proxy limit to {limit} requests per second.",
          "pending_action", "{h2} must raise the staging proxy limit to {limit} requests per second.",
          "{h2} raises the staging proxy limit to {limit} requests per second"),
        E("agent_step", "a1", "Added a unit test for the backoff schedule.",
          "completed", "{a1} added a unit test for the backoff schedule."),
    ),
)

# --- Template 5: a rollback, as the live service leaves the log -----------------------------
# The service deletes events with seq > to_seq and resets the next seq to to_seq + 1, so a
# late joiner never sees the rolled-back edits. Here the rewrite was rolled back to seq 2. The
# `rollback` event is one a client appends afterwards (the service itself appends none) and
# carries the reason. Sequences stay gap-free: 1, 2, then 3 onward.
ROLLBACK = Scenario(
    key="rollback",
    keys=("doc", "competitor"),
    pools=(
        ("launch-plan.md", "Northwind"),
        ("pricing-brief.md", "Contoso"),
        ("gtm-notes.md", "Fabrikam"),
    ),
    ranges=(("faq", 2, 5),),
    events=(
        E("instruction", "h1", "{a1}, rewrite the pricing section of {doc} using the new tiers."),
        E("agent_step", "a1", "Plan: replace the three old tiers with Starter, Team, and Enterprise, then update the comparison table."),
        E("rollback", "h2", "Rolled back {doc} to before the pricing rewrite because finance has not approved the new tiers. Two edits were removed.",
          "completed", "{doc} was rolled back to its state before the pricing rewrite because finance has not approved the new tiers.",
          "{doc} is rolled back to before the pricing rewrite"),
        E("agent_step", "a1", "Confirmed: the pricing section of {doc} shows the three old tiers again."),
        E("instruction", "h2", "Finance will confirm the tiers on Thursday. Hold the rewrite until then.",
          "decision", "The pricing rewrite is on hold until finance confirms the tiers on Thursday.",
          "the pricing rewrite is on hold until Thursday"),
        E("instruction", "h1", "I will ask finance for written approval of the tiers.",
          "pending_action", "{h1} will ask finance for written approval of the tiers.",
          "{h1} asks finance for written approval"),
        E("agent_step", "a1", "Meanwhile I am drafting the FAQ section of {doc}."),
        E("tool_call", "a1", "web_search {competitor} pricing page"),
        E("tool_result", "a1", "Search failed: the search tool returned HTTP 503 twice."),
        E("agent_step", "a1", "The {competitor} pricing comparison is blocked because web_search is unavailable.",
          "blocked", "The {competitor} pricing comparison is blocked because web_search is unavailable.",
          "web_search is unavailable", (-1,)),
        E("doc_update", "a1", "Added {faq} of 8 FAQ answers to {doc}. The rest are still to write.",
          "in_progress", "{a1} has added {faq} of 8 FAQ answers to {doc}.",
          "{faq} of 8 FAQ answers are written"),
        E("agent_step", "a1", "Saved the FAQ draft and paused until finance answers."),
    ),
)

SCENARIOS: tuple[Scenario, ...] = (FEATURE, BLOCKED_TOOL, HANDOFF, ARBITRATION, ROLLBACK)


@dataclass(frozen=True)
class Blueprint:
    """A filled-in session: events plus gold claims and facts keyed by event sequence."""

    session_id: str
    scenario: str
    query: str
    events: list[dict[str, Any]]
    labels: dict[str, str]
    # (category label, text, supporting event ids, fact text or None)
    claims: list[tuple[str, str, list[str], str | None]]


def instantiate(session_no: int, scenario: Scenario, rng: random.Random) -> Blueprint:
    """Fill one scenario. All randomness comes from ``rng``, in a fixed order."""
    h1, h2 = rng.sample(HUMANS, 2)
    a1, a2 = rng.sample(AGENTS, 2)
    params: dict[str, Any] = {"h1": h1, "h2": h2, "a1": a1, "a2": a2}
    row = rng.choice(scenario.pools)
    params.update(zip(scenario.keys, row, strict=True))
    for name, low, high in scenario.ranges:
        params[name] = rng.randint(low, high)
    actors = {"h1": f"human-{h1.lower()}", "h2": f"human-{h2.lower()}",
              "a1": f"agent-{a1.lower()}", "a2": f"agent-{a2.lower()}"}

    sid = f"smoke-s{session_no:02d}"
    ids = [f"{sid}-e{i:03d}" for i in range(1, len(scenario.events) + 1)]
    events: list[dict[str, Any]] = []
    labels: dict[str, str] = {}
    claims: list[tuple[str, str, list[str], str | None]] = []
    for i, ev in enumerate(scenario.events):
        events.append(
            {
                "source_event_id": ids[i],
                "sequence": i + 1,
                "event_type": ev.type,
                "actor_id": actors[ev.who] if ev.who else None,
                "text": ev.text.format(**params),
            }
        )
        if ev.label:
            assert ev.claim, f"{scenario.key} event {i + 1}: label without claim"
            labels[ids[i]] = ev.label
            support = sorted([i, *(i + off for off in ev.also)])
            claims.append(
                (
                    ev.label,
                    ev.claim.format(**params),
                    [ids[j] for j in support],
                    ev.fact.format(**params) if ev.fact else None,
                )
            )
    query = rng.choice(GENERIC_QUERIES)
    return Blueprint(sid, scenario.key, query, events, labels, claims)
