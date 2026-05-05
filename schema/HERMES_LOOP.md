---
name: hermes-self-improvement-loop
description: Design for the Hermes feedback substrate (`_hermes_feedback.jsonl`) and the planned inner (skills) and outer (schema) loops that consume it. Substrate ships with the MVP; loops are stubbed.
---

# Hermes — Self-Improvement Loops

PropContext does not stay frozen after deployment. Every successful ingest writes one JSONL feedback line; later loops consume those lines to propose changes — to the wiki maintainer's playbook (inner) and to the schema itself (outer). The substrate is real; the loops are stubbed.

## 1. Feedback substrate (`_hermes_feedback.jsonl`)

One file per property at `wiki/<LIE-id>/_hermes_feedback.jsonl`. Append-only. One JSON object per line. Written by `apply_patch_plan` after ops are applied and before the git commit, so the feedback line is part of the same audit commit as the markdown changes.

Line shape (MVP):

```json
{
  "kind": "ingest",
  "ts": "2026-04-25T12:32:03.675000+00:00",
  "event_id": "EMAIL-12044",
  "event_type": "email",
  "property_id": "LIE-001",
  "summary": "heating outage reported for EH-014",
  "applied_ops": 8,
  "deferred_ops": 0,
  "touched": ["02_buildings/HAUS-12/index.md", "..."]
}
```

Fields are lower_snake_case. New optional fields may be added; never reshape existing fields.

The writer is idempotent on `event_id`: if a line with the same `event_id` is already present, no new line is written. This protects against re-runs after a crash between markdown write and git commit.

The path begins with `_`, so it is runtime-managed: no patch op may target it. The patcher writes the line directly via `app/services/hermes/feedback.py`.

## 2. Inner loop — skills (closed)

Two layers:

**(a) Detector → `06_skills.md`.** Groups substrate rows by `(event_type, op-shape signature)` where op shapes carry op kind + path template + heading. Any group hitting `min_occurrences` (default 5 for promotion, 3 for prompt-feedback) gets written into `06_skills.md` as a skill candidate.

**(b) Feedback into the extract prompt.** `app/services/hermes/registry.py` builds a `SkillRegistry` indexed by `event_type` from the substrate; the supervisor calls `registry.find_for(event.event_type)` and, when matched, injects a `format_briefing(...)` block into the user prompt before the JSON payload. The briefing names the modal op-shape sequence, the touched-path templates with `<id>` placeholders, and recent summaries.

This is real closure: every applied event improves the next event's prompt. The LLM is not bypassed — body content still requires reasoning — but it now starts each call with a worked example of what the prior pattern looked like, which compounds consistency over time.

Promotion bar: 5 matching events for the public skill page; 3 for prompt-feedback (cheaper signal).

## 3. Outer loop — schema (closed)

Watches the substrate for misses: events that produced few ops, that frequently land in `_pending_review.md`, that mention IDs no entity page resolves. Proposes amendments to:

- `schema/WIKI_SCHEMA.md` — new top-level dirs or section conventions
- `schema/VOCABULARY.md` — new controlled values
- `schema/LEGAL_MAP.md` — new obligations

Output: `_hermes_proposals.md` inside the property tree (always), plus an optional `hermes/proposals-<date>-<property>` git branch when `run_hermes_loops(..., auto_branch=True)` is set or `python -m app.tools.hermes_run --auto-branch` is invoked. The branch carries the proposal markdown with `event_id` evidence in the commit body, ready for review. Branches are never auto-merged.

## 4. Schema proposal protocol

When the outer loop wants to add a controlled value or legal obligation:

1. Append a row to the relevant table (`VOCABULARY.md`, `LEGAL_MAP.md`).
2. Reference the substrate evidence: list of `event_id`s in the proposal commit body.
3. Open the change as a `hermes/propose-<slug>` branch + PR draft.
4. Never delete a row in the same proposal — removals require Tier B Archive-First with a git tag (per `WIKI_SCHEMA.md §16`).

## 5. Why this works

The substrate is cheap (one JSONL line per ingest) and survives every code change: it carries forward across migrations because it lives inside the property tree under git. Loops 2 and 3 can be added — or replaced — without re-plumbing the feedback path.

## 6. Status

| Layer | State |
|---|---|
| §1 Substrate | Implemented (with `op_shapes` per row) |
| §2 Inner skill loop | Implemented (detector + prompt feedback wired into supervisor) |
| §3 Outer schema loop | Implemented (proposal markdown + optional `hermes/` branch) |
| §4 Proposal protocol | Implemented (auto-branch carries evidence in commit body) |
