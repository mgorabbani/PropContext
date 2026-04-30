# Ingestion Simulation

This document simulates what happens after a new source event arrives and how
the markdown context is updated from start to finish.

The product language says "one building.md per property." In the current code
and schema, that file is represented as `wiki/<property_id>/index.md`, with
supporting markdown files under the same property folder. Building-specific
markdown is served from `wiki/<property_id>/02_buildings/<building_id>/index.md`.

## Current implementation snapshot

The implemented ingestion path is:

1. `POST /api/v1/webhook/ingest`
2. HMAC verification and `IngestEvent` validation
3. API-level idempotency claim in `output/idempotency.duckdb`
4. `Supervisor.handle(event)`
5. event handler normalization into `normalize/.../*.md`
6. signal classification through `classify_document`
7. entity resolution through `stammdaten.duckdb`
8. target-section lookup through `wiki_chunks.duckdb`
9. LLM extraction of a `PatchPlan`
10. conflict scan
11. deterministic patch application to `wiki/<property_id>/*.md`
12. `_hermes_feedback.jsonl` append
13. git commit in `wiki_dir`
14. reindex touched markdown files into `wiki_chunks.duckdb`
15. idempotency marked `done`
16. webhook response returned

The schema docs also describe optional SSE broadcast and Hermes inner/outer
loops. Those are part of the intended concept, but they are not wired into the
current synchronous webhook code path yet.

## Component map

| Component | Code/docs | Role |
|---|---|---|
| Webhook API | `app/api/v1/webhook.py` | Accepts signed ingest events, rejects bad signatures, enforces replay protection, calls the supervisor. |
| Event schema | `app/schemas/webhook.py` | Defines `event_id`, `event_type`, `property_id`, optional `source_path`, and free-form `payload`. |
| Idempotency store | `app/storage/idempotency.py` | Stores `event_id` as `pending`, `done`, or `failed`; prevents duplicate webhook work. |
| Supervisor | `app/services/supervisor.py` | Orchestrates normalize, classify, resolve, locate, extract, conflict scan, patch, reindex. |
| Event handlers | `app/services/handlers/*` | Convert source-specific inputs into normalized markdown. Current direct handler keys include `email`, `eml`, `invoice`, `bank`, `letter`, `manual`, `document`, `schedule`, `lint`, `erp`, `chat`, `slack`, `whatsapp`, and `voicenote`. |
| Normalizers | `app/services/normalize/*` | Parse `.eml`, invoice/letter PDFs, and bank rows into markdown under `normalize/`. |
| Classifier | `app/services/classify.py` | Uses a small LLM prompt over sender, subject, and excerpt to decide signal/noise. No signal means no wiki patch. |
| Resolver | `app/services/resolve.py` | Uses email, IBAN, and explicit IDs to map a source to `MIE-*`, `EIG-*`, `EH-*`, `HAUS-*`, `DL-*`, and source IDs. |
| Stammdaten store | `app/storage/stammdaten.py` | DuckDB cache loaded from `data/stammdaten/stammdaten.json`; source of entity identity. |
| Wiki chunks | `app/storage/wiki_chunks.py`, `app/services/reindex.py` | Derived DuckDB index of markdown sections. Used to find likely target sections and for search. |
| Extractor | `app/services/extract.py` | Sends normalized source plus located sections to the larger LLM and receives a canonical `PatchPlan`. |
| Conflict scanner | `app/services/conflict.py` | Defers risky overwrites such as status flips, large date drift, or amount deltas to `_pending_review.md`. |
| Patcher | `app/services/patcher/apply.py`, `app/services/patcher/ops.py` | Applies line-based markdown operations. No LLM at apply time. Refuses writes outside managed sections before `# Human Notes`. |
| Atomic writer | `app/services/patcher/atomic.py` | Writes via temp file, fsync, and replace. |
| Vocabulary | `schema/VOCABULARY.md` | Controlled values checked before patching. Unknown values become pending-review items. |
| Wiki schema | `schema/WIKI_SCHEMA.md`, `schema/CLAUDE.md` | Canonical markdown layout, sections, patch operation rules, conflict policy, and long-term Hermes plan. |
| Read API | `app/api/v1/properties.py`, `app/services/wiki.py` | Serves property and building markdown as `text/markdown`. |

Note: schema examples use dotted event names like `email.received`. The current
handler registry does not map dotted names yet; `email.received` would fall
back to `DocumentHandler` unless the registry is expanded. This simulation uses
the current code-compatible event type `email`.

## Scenario

A tenant reports a heating outage in unit `EH-014`. The source adapter sends a
signed webhook event for property `LIE-001`.

Sample webhook body:

```json
{
  "event_id": "EMAIL-12044",
  "event_type": "email",
  "property_id": "LIE-001",
  "source_path": "data/emails/2026-04/20260425_143200_EMAIL-12044.eml",
  "payload": {}
}
```

Assumed raw email content:

```text
From: anna.mueller@example.test
To: pm@example.test
Date: Sat, 25 Apr 2026 14:32:00 +0200
Subject: Heizung kalt in EH-014

Hallo,
in EH-014 ist die Heizung seit heute Mittag kalt. Bitte schicken Sie den
Heizungsdienst. Die Wohnung ist in HAUS-12.
Viele Gruesse
Anna Mueller
```

## Timestamped event log

| Time | Step | Component | What happened | Data read/written |
|---|---|---|---|---|
| 2026-04-25T14:32:00.000+02:00 | source event | Mail adapter | New tenant email is detected and mapped to `event_id=EMAIL-12044`. | Reads mailbox; prepares webhook JSON. |
| 2026-04-25T14:32:00.180+02:00 | webhook received | FastAPI webhook | `POST /api/v1/webhook/ingest` receives raw bytes. | Reads request body. |
| 2026-04-25T14:32:00.184+02:00 | verify signature | `_verify_hmac` | Computes HMAC SHA-256 using `APP_WEBHOOK_HMAC_SECRET`; compares with `x-propcontext-signature`. | No files written. |
| 2026-04-25T14:32:00.188+02:00 | parse event | `_parse_event` | JSON is parsed into `IngestEvent`. | In-memory event object. |
| 2026-04-25T14:32:00.194+02:00 | claim event | `IdempotencyStore.claim` | `EMAIL-12044` is inserted as `pending`. | Writes `output/idempotency.duckdb`. |
| 2026-04-25T14:32:00.205+02:00 | dispatch | `get_event_handler` | `event_type=email` routes to `EmailHandler`. | In-memory handler selection. |
| 2026-04-25T14:32:00.215+02:00 | normalize | `EmailHandler` and `normalize_eml` | Source `.eml` is parsed with Python email parser. | Reads `data/emails/2026-04/20260425_143200_EMAIL-12044.eml`. |
| 2026-04-25T14:32:00.265+02:00 | write normalized source | `write_normalized_markdown` | Normalized markdown is written with source, sha256, parser, parsed time, mime, language. | Writes `normalize/eml/2026-04/EMAIL-12044.md`. |
| 2026-04-25T14:32:00.310+02:00 | classify prompt | `classify_document` | Classifier sees sender, subject, and first 500 chars. | Sends LLM request using `settings.haiku_model`. |
| 2026-04-25T14:32:00.980+02:00 | classify result | `Classification` | Email is considered signal: category `task_update/heating`, priority `high`, confidence `0.93`. | No files written. |
| 2026-04-25T14:32:01.005+02:00 | open master data | `_open_stammdaten` | `stammdaten.duckdb` is opened; if empty, JSON master data is loaded. | Reads `data/stammdaten/stammdaten.json`; writes `output/stammdaten.duckdb` if needed. |
| 2026-04-25T14:32:01.035+02:00 | resolve entities | `resolve_context` | Sender email maps to tenant, explicit `EH-014` and `HAUS-12` are validated. Related owner/unit/building chain is collected. | In-memory `ResolutionResult`. |
| 2026-04-25T14:32:01.065+02:00 | open section index | `open_wiki_chunks` | The wiki section cache is opened. If the property wiki exists but has no rows, it is reindexed. | Reads/writes `output/wiki_chunks.duckdb`. |
| 2026-04-25T14:32:01.090+02:00 | locate sections | `locate_sections` | Finds candidate sections by entity refs first, then full-text query fallback. | Reads `wiki_chunks` rows. |
| 2026-04-25T14:32:01.130+02:00 | extraction prompt | `extract_patch_plan` | Sends normalized email, resolved IDs, source IDs, and located section bodies to extractor. | Sends LLM request using `settings.sonnet_model`. |
| 2026-04-25T14:32:03.420+02:00 | patch plan returned | `canonicalize_patch_plan` | LLM output is normalized: wiki-prefixed paths become property-relative paths, `content` becomes `text` or `row`. | In-memory `PatchPlan`. |
| 2026-04-25T14:32:03.455+02:00 | conflict scan | `scan_patch_plan_conflicts` | Existing keyed lines are checked for status flip, date drift, or amount delta. No conflict found. | Reads target markdown files. |
| 2026-04-25T14:32:03.480+02:00 | vocabulary validation | `validate_keyed_values` | Controlled values are checked. Invalid ops would be moved to `_pending_review.md`. | Reads `schema/VOCABULARY.md`. |
| 2026-04-25T14:32:03.505+02:00 | patch open issue | `upsert_bullet` | Inserts or replaces the keyed `EH-014` issue line in `HAUS-12/index.md`. | Writes `wiki/LIE-001/02_buildings/HAUS-12/index.md`. |
| 2026-04-25T14:32:03.535+02:00 | patch recent event | `prepend_row` | Adds newest event row at top of the `Recent Events` table. | Writes `wiki/LIE-001/02_buildings/HAUS-12/index.md`. |
| 2026-04-25T14:32:03.565+02:00 | patch unit history | `prepend_row` | Adds the event to the unit dossier history. | Writes `wiki/LIE-001/02_buildings/HAUS-12/units/EH-014.md`. |
| 2026-04-25T14:32:03.595+02:00 | patch tenant contact | `prepend_row` | Adds the email to tenant contact history. | Writes `wiki/LIE-001/03_people/mieter/MIE-014.md`. |
| 2026-04-25T14:32:03.625+02:00 | patch provenance | `upsert_footnote` | Adds source footnotes in every file that references `EMAIL-12044`. | Writes `## Provenance` sections only. |
| 2026-04-25T14:32:03.650+02:00 | patch state | `update_state` | Updates `last_event_id`, increments counters, and sets `last_patched`. | Writes `wiki/LIE-001/_state.json`. |
| 2026-04-25T14:32:03.675+02:00 | append feedback | `_append_feedback` | Records the ingest summary and op counts. | Writes `wiki/LIE-001/_hermes_feedback.jsonl`. |
| 2026-04-25T14:32:03.720+02:00 | commit | `_git_commit` | Stages all wiki changes and creates one audit commit. | Runs `git add -A`; commit message `ingest(EMAIL-12044): heating outage reported for EH-014`. |
| 2026-04-25T14:32:03.820+02:00 | reindex touched files | `_reindex_touched_files` | Parses touched markdown sections and refreshes section rows. | Writes `output/wiki_chunks.duckdb`. |
| 2026-04-25T14:32:03.855+02:00 | mark done | `IdempotencyStore.mark_done` | Event status becomes `done`. | Writes `output/idempotency.duckdb`. |
| 2026-04-25T14:32:03.870+02:00 | response | `IngestResponse` | API returns `status=applied`, applied/deferred op counts, commit SHA, `idempotent=false`. | HTTP JSON response. |
| 2026-04-25T14:32:04.000+02:00 | read side available | `WikiService` | External agents can fetch updated markdown. | `GET /api/v1/properties/LIE-001/buildings/HAUS-12`. |

## Normalized source markdown

The first persistent artifact is not the wiki patch. It is the normalized source
markdown. This gives the patch provenance a stable, readable source file.

Example `normalize/eml/2026-04/EMAIL-12044.md`:

```markdown
---
source: "data/emails/2026-04/20260425_143200_EMAIL-12044.eml"
sha256: "9c0d...sample"
parser: "python-email"
parsed_at: "2026-04-25T12:32:00.265000+00:00"
mime: "message/rfc822"
lang: "de"
---
# Email EMAIL-12044

| Field | Value |
|---|---|
| ID | EMAIL-12044 |
| Subject | Heizung kalt in EH-014 |
| From | Anna Mueller <anna.mueller@example.test> |
| To | pm@example.test |
| Date | Sat, 25 Apr 2026 14:32:00 +0200 |
| Message-ID | <EMAIL-12044@example.test> |

## Body

Hallo,
in EH-014 ist die Heizung seit heute Mittag kalt. Bitte schicken Sie den
Heizungsdienst. Die Wohnung ist in HAUS-12.
Viele Gruesse
Anna Mueller
```

## Resolved context

Example in-memory resolution:

```json
{
  "property_id": "LIE-001",
  "entities": [
    {"id": "MIE-014", "role": "mieter", "source": "email"},
    {"id": "EH-014", "role": "einheit", "source": "email"},
    {"id": "EIG-009", "role": "eigentuemer", "source": "email"},
    {"id": "HAUS-12", "role": "gebaeude", "source": "email"}
  ],
  "mentioned_ids": ["EH-014", "HAUS-12"],
  "source_ids": ["EMAIL-12044"],
  "unresolved_ids": []
}
```

Example located sections from `wiki_chunks.duckdb`:

```json
[
  {
    "file": "02_buildings/HAUS-12/index.md",
    "section": "Open Issues",
    "entity_refs": ["HAUS-12", "EH-014"],
    "score": 10.0
  },
  {
    "file": "02_buildings/HAUS-12/index.md",
    "section": "Recent Events",
    "entity_refs": ["HAUS-12"],
    "score": 10.0
  },
  {
    "file": "02_buildings/HAUS-12/units/EH-014.md",
    "section": "History",
    "entity_refs": ["EH-014", "MIE-014", "EIG-009"],
    "score": 10.0
  },
  {
    "file": "03_people/mieter/MIE-014.md",
    "section": "Contact History",
    "entity_refs": ["MIE-014", "EH-014"],
    "score": 10.0
  }
]
```

## PatchPlan

This is the canonical patch plan after extraction and path normalization. The
actual patcher applies these operations deterministically; it does not ask an
LLM to edit markdown.

```json
{
  "event_id": "EMAIL-12044",
  "property_id": "LIE-001",
  "event_type": "email",
  "summary": "heating outage reported for EH-014",
  "source_ids": ["EMAIL-12044"],
  "ops": [
    {
      "op": "upsert_bullet",
      "file": "02_buildings/HAUS-12/index.md",
      "section": "Open Issues",
      "key": "EH-014",
      "text": "- 🔴 **EH-014:** Heating outage reported by MIE-014 on 2026-04-25; heating service requested [^EMAIL-12044]"
    },
    {
      "op": "prepend_row",
      "file": "02_buildings/HAUS-12/index.md",
      "section": "Recent Events",
      "row": ["2026-04-25 14:32", "HAUS-12", "email", "Heating outage EH-014", "[^EMAIL-12044]"],
      "header": ["Date", "Scope", "Type", "Summary", "Source"]
    },
    {
      "op": "prepend_row",
      "file": "02_buildings/HAUS-12/units/EH-014.md",
      "section": "History",
      "row": ["2026-04-25", "email", "Tenant reported no heating", "[^EMAIL-12044]"],
      "header": ["Date", "Type", "Summary", "Source"]
    },
    {
      "op": "prepend_row",
      "file": "03_people/mieter/MIE-014.md",
      "section": "Contact History",
      "row": ["2026-04-25", "email", "Reported heating outage in EH-014", "[^EMAIL-12044]"],
      "header": ["Date", "Type", "Summary", "Source"]
    },
    {
      "op": "upsert_footnote",
      "file": "02_buildings/HAUS-12/index.md",
      "key": "EMAIL-12044",
      "text": "normalize/eml/2026-04/EMAIL-12044.md"
    },
    {
      "op": "upsert_footnote",
      "file": "02_buildings/HAUS-12/units/EH-014.md",
      "key": "EMAIL-12044",
      "text": "normalize/eml/2026-04/EMAIL-12044.md"
    },
    {
      "op": "upsert_footnote",
      "file": "03_people/mieter/MIE-014.md",
      "key": "EMAIL-12044",
      "text": "normalize/eml/2026-04/EMAIL-12044.md"
    },
    {
      "op": "update_state",
      "file": "_state.json",
      "updates": {"last_event_id": "EMAIL-12044"},
      "counters": {"open_issues": 1}
    }
  ],
  "review_items": [],
  "complexity_score": 5,
  "skill_candidate": false
}
```

## Markdown write simulation

Only managed sections before `# Human Notes` are changed. Human notes and
unkeyed human bullets are preserved.

Before `wiki/LIE-001/02_buildings/HAUS-12/index.md`:

```markdown
## Open Issues

<!-- agent-managed: keyed bullets, format `- 🔴 **EH-XX:** ... [^source]` -->

## Recent Events

<!-- agent-managed: ring buffer max=50 -->

## Provenance

<!-- agent-managed: footnote definitions only -->

# Human Notes

Tenant called twice last winter about radiator noise. Keep this note.
```

After `wiki/LIE-001/02_buildings/HAUS-12/index.md`:

```markdown
## Open Issues

<!-- agent-managed: keyed bullets, format `- 🔴 **EH-XX:** ... [^source]` -->
- 🔴 **EH-014:** Heating outage reported by MIE-014 on 2026-04-25; heating service requested [^EMAIL-12044]

## Recent Events

<!-- agent-managed: ring buffer max=50 -->
| Date | Scope | Type | Summary | Source |
| --- | --- | --- | --- | --- |
| 2026-04-25 14:32 | HAUS-12 | email | Heating outage EH-014 | [^EMAIL-12044] |

## Provenance

<!-- agent-managed: footnote definitions only -->
[^EMAIL-12044]: normalize/eml/2026-04/EMAIL-12044.md

# Human Notes

Tenant called twice last winter about radiator noise. Keep this note.
```

After `wiki/LIE-001/02_buildings/HAUS-12/units/EH-014.md`:

```markdown
## History

<!-- agent-managed: prepend rows, ring buffer -->
| Date | Type | Summary | Source |
| --- | --- | --- | --- |
| 2026-04-25 | email | Tenant reported no heating | [^EMAIL-12044] |

## Provenance

<!-- agent-managed: footnote definitions only -->
[^EMAIL-12044]: normalize/eml/2026-04/EMAIL-12044.md

# Human Notes
```

After `wiki/LIE-001/03_people/mieter/MIE-014.md`:

```markdown
## Contact History

<!-- agent-managed: ring buffer -->
| Date | Type | Summary | Source |
| --- | --- | --- | --- |
| 2026-04-25 | email | Reported heating outage in EH-014 | [^EMAIL-12044] |

## Provenance

<!-- agent-managed: footnote definitions only -->
[^EMAIL-12044]: normalize/eml/2026-04/EMAIL-12044.md

# Human Notes
```

After `wiki/LIE-001/_state.json`:

```json
{
  "schema_version": 1,
  "property_id": "LIE-001",
  "bootstrapped_at": "2026-04-25T10:00:00+00:00",
  "last_patched": "2026-04-25T12:32:03.650000+00:00",
  "last_event_id": "EMAIL-12044",
  "counts": {
    "buildings": 3,
    "units": 52,
    "owners": 35,
    "tenants": 26,
    "dienstleister": 16,
    "open_issues": 1
  }
}
```

After `wiki/LIE-001/_hermes_feedback.jsonl`:

```jsonl
{"kind":"ingest","event_id":"EMAIL-12044","property_id":"LIE-001","summary":"heating outage reported for EH-014","applied_ops":8,"deferred_ops":0}
```

The current code writes a compact feedback line with event ID, property ID,
summary, applied op count, and deferred op count. The richer JSONL shape in
`schema/HERMES_LOOP.md` is the planned self-improvement substrate.

## Webhook response

Example response:

```json
{
  "event_id": "EMAIL-12044",
  "status": "applied",
  "applied_ops": 8,
  "deferred_ops": 0,
  "commit_sha": "a3f2c19b6d8e4f0a9b1c2d3e4f5a6b7c8d9e0f1a",
  "idempotent": false
}
```

## Duplicate replay

If the same webhook arrives again:

1. `IdempotencyStore.claim("EMAIL-12044")` sees status `done`.
2. The supervisor is not called.
3. The API returns:

```json
{
  "event_id": "EMAIL-12044",
  "status": "duplicate",
  "applied_ops": 0,
  "deferred_ops": 0,
  "commit_sha": null,
  "idempotent": true
}
```

There is also patch-level replay protection: if `_hermes_feedback.jsonl`
already contains the event ID, `apply_patch_plan` returns an idempotent result
without rewriting markdown. This is useful if the API-level DuckDB state is
lost or rebuilt.

## Conflict branch

If `EH-014` already had a contradictory keyed line, the conflict scanner would
drop only the risky op and keep safe ops.

Example existing line:

```markdown
- 🟢 **EH-014:** Heating repaired on 2026-04-24 [^EMAIL-12012]
```

Incoming line:

```markdown
- 🔴 **EH-014:** Heating outage reported by MIE-014 on 2026-04-25 [^EMAIL-12044]
```

Possible result:

```markdown
## Open Conflicts

### conflict: EH-014
- file: `02_buildings/HAUS-12/index.md`
- section: `Open Issues`
- reason: status flip requires human approval
- existing: `- 🟢 **EH-014:** Heating repaired on 2026-04-24 [^EMAIL-12012]`
- incoming: `- 🔴 **EH-014:** Heating outage reported by MIE-014 on 2026-04-25 [^EMAIL-12044]`
```

The webhook would still complete with `status=applied` if other non-conflicting
ops were applied, but `deferred_ops` would be greater than zero.

## What external agents read

After the commit and reindex, the markdown is available through the read API:

```text
GET /api/v1/properties/LIE-001
GET /api/v1/properties/LIE-001/buildings/HAUS-12
```

For this scenario, a building-focused agent would fetch:

```text
wiki/LIE-001/02_buildings/HAUS-12/index.md
```

It now contains the new open issue, the recent event, and a footnote pointing
back to `normalize/eml/2026-04/EMAIL-12044.md`.

## Operational notes

- Bootstrap must run before live ingestion so `wiki/LIE-001/...` files exist
  and contain the expected sections.
- `wiki_dir` must be a git repository with local user config, because each
  applied event creates a commit.
- `wiki_chunks.duckdb` is derived cache. It can be rebuilt from markdown.
- `normalize/` files are provenance artifacts and should not be regenerated in
  a way that changes source IDs.
- `# Human Notes` is the hard boundary. The patcher works only on managed
  sections above it.
- Current code writes property context to `wiki/<property_id>/index.md`, not to
  `output/building.md`. If the deliverable must be literally named
  `building.md`, add an export or compatibility layer rather than changing the
  canonical wiki layout.
