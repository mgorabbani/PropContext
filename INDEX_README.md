# BaC — Building-as-Code: `template_index.md`

> **BerlinHackBuena · Hermes-Wiki Engine**  
> Schema v1 · Template v1.1.0

This README covers everything a teammate needs to understand, use, extend, or debug `template_index.md` — the structural blueprint for every building context file in the wiki.

---

## What this file is

`template_index.md` is the canonical schema for every `wiki/{{LIE_ID}}/{{HAUS_ID}}/index.md` file in the BaC system. It defines:

- Which sections exist, in what order, and why
- What each section contains and who writes to it
- Token budget per section (for RAG performance)
- Freshness ceilings (for the nightly Linter)
- The Hermes self-improvement loop trigger logic
- The Archive-First data-loss guardrail protocol

**Primary consumer:** AI agent (chunk-level RAG retrieval)  
**Secondary consumer:** Human PM (read + annotations in PM Notes only)

The Patcher agent uses this as its **write contract**. The Linter agent uses it as its **validation contract**. If you change the template, you must propagate changes to all existing `HAUS-*.md` files (the Periodic Nudge handles this — see below).

---

## Repository placement

```
wiki/
├── template_index.md       ← this file's template
├── README.md               ← this file
├── WIKI_SCHEMA.md          ← full schema contract (Patcher/Linter source of truth)
├── index.md                ← global Liegenschaft catalog
└── LIE-001/
    ├── HAUS-12/
    │   ├── index.md        ← generated from template_index.md
    │   ├── EH-001.md
    │   ├── _hermes_feedback.jsonl
    │   └── _archive/
    │       └── HAUS-12/
    ├── eigentuemer/
    ├── mieter/
    └── dienstleister/
```

---

## Section map

The file has **18 sections** across four tiers. Order is intentional — it encodes retrieval priority for the RAG system.

### Tier 0 — Critical (sections 1–3)
Always retrieved for any query. Staleness ceiling: **30 days** for all three.

| # | Section key | Purpose | Token ceiling |
|---|---|---|---|
| 1 | `emergency_dispatch` | Dispatch table for every emergency scenario | 200 |
| 2 | `active_critical_issues` | 🔴 issues requiring action within 48h only | 200 |
| 3 | `access_and_security` | Keybox codes, room access, alarm PINs | 150 |

### Tier 1 — Dynamic (sections 4–9)
Covers ~80% of PM agent operational tasks. Staleness ceilings vary.

| # | Section key | Purpose | Freshness | Token ceiling |
|---|---|---|---|---|
| 4 | `open_issues` | Full issue register — all severities | 14d | 500 |
| 5 | `tenancy_snapshot` | EH → Mieter → payment status snapshot | 30d | 500 |
| 6 | `contractor_roster` | Active DL directory with SLA | 90d | 400 |
| 7 | `procedural_memory` | Extracted Hermes skills and workflows | 180d | 500 |
| 8 | `recent_events` | Rolling 60-day event log | daily | 500 |
| 9 | `weg_compliance` | ETV, Verwaltervertrag, Beschlüsse, Rücklage formula | 90d | 400 |

### Tier 2 — Static (sections 10–16)
Deep and historical queries. Slow decay.

| # | Section key | Purpose | Freshness | Token ceiling |
|---|---|---|---|---|
| 10 | `core_metadata` | Address, Baujahr, MEA, Energieausweis | 365d | 300 |
| 11 | `physical_infrastructure` | MEP lifecycle — Heizung, Dach, Steigleitungen, Rauchwarnmelder | 90d | 500 |
| 12 | `financial_snapshot` | Konten, Rücklage adequacy verdict, Hausgeld | 90d | 400 |
| 13 | `unit_register` | One-line per EH: m², MEA, owner, tenant, status | 90d | 500 |
| 14 | `legal_documents` | Teilungserklärung, Verwaltervertrag, Versicherung index | 365d | 300 |
| 15 | `archive_index` | Append-only log of all archived content | N/A | 300 |
| 16 | `provenance` | Source footnotes for every fact in the file | N/A | 500 |

### Meta (sections 17–18)
Machine-managed. Human: read-only for audit.

| # | Section key | Purpose | Token ceiling |
|---|---|---|---|
| 17 | `hermes_meta` | Loop state + full trigger specification | 400 |
| 18 | `schema_evolution` | Template version history (Karpathy format) | 200 |

---

## How a new `HAUS-XX/index.md` is created

1. Copy `template_index.md` to `wiki/{{LIE_ID}}/{{HAUS_ID}}/index.md`
2. Replace all `{{PLACEHOLDER}}` values (see placeholder reference below)
3. Populate Tier 0 sections manually or via Patcher from `stammdaten.json`
4. Set `health_score: 0.00` — Linter will compute the real value on its first nightly run
5. Set `hermes_nudge_counter: 0` — Hermes loop starts fresh
6. Commit: `git commit -m "init: {{HAUS_ID}} index from template v1.1.0"`

The Patcher agent can automate steps 2–4 given `stammdaten.json` as input.

---

## Placeholder reference

| Placeholder | Example value | Set by |
|---|---|---|
| `{{HAUS_ID}}` | `HAUS-12` | Manual / Patcher |
| `{{LIE_ID}}` | `LIE-001` | Manual / Patcher |
| `{{HAUS_BEZEICHNUNG}}` | `Vorderhaus` | Manual |
| `{{ISO_TIMESTAMP}}` | `2026-04-25T10:00:00Z` | Patcher |
| `{{GIT_HASH}}` | `a3f2c19` | Patcher (post-commit) |
| `{{STRASSE}}`, `{{NR}}`, `{{PLZ}}`, `{{STADT}}` | `Immanuelkirchstraße`, `26`, `10405`, `Berlin` | stammdaten.json |
| `{{HAUS_TYP}}` | `Vorderhaus` | stammdaten.json |
| `{{QM_TOTAL}}` | `1240.5` | stammdaten.json |
| `{{BAUJAHR}}` | `1908` | stammdaten.json |
| `{{DL_HAUSMEISTER}}`, `{{DL_HEIZUNG}}`, etc. | `DL-003`, `DL-007` | stammdaten.json |
| `{{TEL}}` | `+49 30 555-0123` | dienstleister.csv |
| `{{VERWALTER_TEL}}` | internal | config |

All `{{A\|B\|C}}` placeholders are pick-one enumerations — remove the pipe-separated options and leave only the chosen value.

---

## Anchor write rules (what Patcher must obey)

These rules are the contract between this template and the Patcher agent. Violations corrupt the wiki.

**Never touch outside anchors.** Content between `<!-- @section:KEY version=N -->` and `<!-- @end:KEY -->` is Patcher territory. Everything below `## PM Notes` is human territory. Patcher must not write there under any circumstances.

**Always increment `version=N`.** Every successful patch bumps the version number on the opening anchor tag. This is how the Linter detects whether a section has been touched since a given commit.

**Conflict policy: write to `_pending_review.md`, never overwrite.** If new content from an ingest contradicts an existing fact, Patcher writes both versions to `_pending_review.md` and logs the contradiction in `LIE-001/log.md`. A human PM resolves it.

**Footnotes go in `provenance` only.** New `[^ID]` definitions are always added to the `provenance` section. Never inline inside other sections.

**Archive-First before any deletion.** See the Archive-First protocol section below.

---

## Archive-First protocol

Before Patcher removes any content from any section, it must execute all five steps:

```
STEP 1  Write full section content to:
        _archive/{{HAUS_ID}}/YYYY-MM-DD_{{section_key}}_v{{N}}.md
        File must include the section content + all its provenance footnotes.

STEP 2  Create git tag:
        archive/{{HAUS_ID}}/{{section_key}}/v{{N}}

STEP 3  Append a row to archive_index section in index.md.

STEP 4  Append an entry to LIE-001/log.md with reason + patcher_commit.

STEP 5  Only then: remove or overwrite the original content.
```

This guarantees that any historical fact is reconstructable from the wiki alone, without accessing raw source files (`normalize/`, `raw/`). This is the answer to the Completeness Contract stated in the frontmatter.

---

## Hermes self-improvement loop

The Hermes loop governs how the wiki improves itself over time. It uses a **hybrid trigger model** — three mechanisms that fire independently.

### Trigger 1 — Event (primary)

**Fires after every ingest task where `tool_calls ≥ skill_extraction_threshold` (default: 5).**

The Patcher runs LLM skill extraction over the task trajectory, writes or updates a `@skill` block in `procedural_memory`, increments `hermes_nudge_counter` in the frontmatter, and appends a JSONL entry to `_hermes_feedback.jsonl`:

```json
{
  "ts": "2026-04-25T14:32:11Z",
  "ingest_id": "EMAIL-12044",
  "tool_calls": 7,
  "sections_read": ["emergency_dispatch", "contractor_roster", "open_issues"],
  "sections_patched": ["open_issues", "recent_events"],
  "retrieval_success": true,
  "missing_context": null,
  "correction_applied": false,
  "skill_extracted": true,
  "skill_id": "heating-emergency-after-hours"
}
```

### Trigger 2 — Periodic nudge (secondary)

**Fires when `hermes_nudge_counter mod 15 == 0`** — every 15 ingest events.

The Patcher reads the last 15 entries from `_hermes_feedback.jsonl` and runs an LLM evaluation: which sections show repeated `retrieval_success: false`? Which `missing_context` patterns recur? If a structural optimization is identified, it writes a proposal to `_pending_review.md`. The PM approves, and Patcher propagates the change to `template_index.md` and all `HAUS-*.md` files. Archive-First applies to any content removed in the process.

### Trigger 3 — Nightly cron (maintenance)

**Fires on a schedule, independent of ingest volume.**

Recomputes `health_score`, flags sections where `last_patched > FRESHNESS_CEILING` as `stale_facts`, detects contradictions across anchor sections, and updates the derived counters in the frontmatter. Commits as: `cron: health+freshness audit YYYY-MM-DD`.

### Why JSONL and not Markdown tickets?

JSONL is machine-queryable without a parser, importable into SQLite for FTS5 search (matching the Hermes Agent native architecture), compressible for archiving, and structurally consistent across all ingest types. Markdown tickets in `_pending_review.md` are reserved for human-facing decisions only.

---

## Health score formula

The Linter computes `health_score` nightly and writes it to the frontmatter:

```
health = 1.0
       - 0.10 × open_issues_count
       - 0.20 × overdue_invoices_count
       - 0.05 × stale_facts_count
       - 0.10 × pending_review_count

clamped to [0.0, 1.0]
```

A score below `0.60` should trigger a PM alert. The global `wiki/index.md` aggregates health scores across all buildings via Obsidian Dataview.

---

## RAG retrieval design

Each `@section` block is an **independent retrieval unit** — a single RAG chunk. The retriever does not see the whole file; it sees individual sections. Two things determine whether the right section is returned:

**Section header quality.** The header line and the first content line of each section carry the highest retrieval weight. They must be semantically specific. `## Notfalldispatch & Sofortmaßnahmen` retrieves correctly on "Gasgeruch" queries. A generic header like `## Section 1` does not.

**Token discipline.** Sections that grow beyond their ceiling dilute retrieval precision. The Linter flags violations; the Patcher splits oversized sections. The split rule for `unit_register` and `tenancy_snapshot` is: split by floor when the section exceeds its ceiling by more than 20%.

---

## Controlled vocabulary

These values are used across sections. Use only the listed options — agents pattern-match on them.

| Field | Allowed values |
|---|---|
| Risk level | `niedrig` \| `mittel` \| `hoch` \| `kritisch` |
| Unit status | `vermietet` \| `leer` \| `leerstehend` \| `Eigenbedarf` \| `Renovierung` |
| Issue priority | `🔴` (≤48h) \| `🟡` (≤14d) \| `🟢` (planned) |
| Issue lifecycle | `offen` \| `zugewiesen` \| `in_progress` \| `gelöst` \| `archiviert` |
| Payment status | `pünktlich` \| `verspätet_<N>d` \| `ausstehend` \| `Widerspruch` |
| Event type | `email` \| `invoice` \| `bank` \| `letter` \| `event` \| `inspection` \| `legal` |

---

## German legal requirements embedded in the template

The template encodes Berlin/WEG-specific legal obligations so the Patcher agent doesn't need to know them independently.

| Requirement | Location in template | Source |
|---|---|---|
| Rauchwarnmelderpflicht | `physical_infrastructure` | §45 Abs. 6 BauO Bln |
| ETV Einladungsfrist 21 Tage | `weg_compliance` | §24 WEGesetz |
| Beschlussfähigkeit >50% MEA | `weg_compliance` | §25 WEGesetz |
| Rücklage-Adequacy-Formel | `weg_compliance` + `financial_snapshot` | §19 WEGesetz |
| Verwaltervertrag Laufzeit | `legal_documents` | §26 WEGesetz |
| TÜV-Pflicht Aufzug | `physical_infrastructure` | BetrSichV §14 |
| E-Check Pflicht | `physical_infrastructure` | DGUV V3 §5 |

---

## How to extend this template

**Adding a new section:** Add it to `template_index.md` with a `<!-- @section:NEW_KEY version=0 -->` anchor, assign it a tier and token ceiling, document the freshness governance rule and prune rule, add it to the section map in this README, and bump `template_version` in the frontmatter. Then run the Patcher propagation task across all existing `HAUS-*.md` files.

**Changing a section's structure:** This is a schema change. Write a proposal to `_pending_review.md`, get PM approval, bump `template_version`, update `schema_evolution`, and propagate. Archive-First applies to any content that the restructuring would remove.

**Removing a section:** Archive-First Protocol is mandatory. No exceptions.

**Changing a token ceiling:** Edit the `retrieval_profile` in the frontmatter and the corresponding `TOKEN_CEILING` annotation in the section comment. The Linter will enforce the new ceiling from the next nightly run.

---

## Files in this directory

| File | Owner | Description |
|---|---|---|
| `template_index.md` | Patcher / Team | The template — this is what you instantiate per building |
| `README.md` | Team | This file |
| `WIKI_SCHEMA.md` | Team | Full schema contract — Patcher and Linter source of truth |
| `wiki/LIE-001/HAUS-*/index.md` | Patcher (sections) + PM (notes) | Instantiated building files |
| `wiki/LIE-001/HAUS-*/_hermes_feedback.jsonl` | Patcher | Hermes loop feedback log — do not edit manually |
| `wiki/LIE-001/HAUS-*/_archive/` | Patcher | Archive-First snapshots — append-only |
| `wiki/LIE-001/_pending_review.md` | Patcher writes, PM resolves | Contradictions and optimization proposals awaiting human decision |
| `wiki/LIE-001/log.md` | Patcher | Append-only event log (Karpathy convention) |
| `schema/skills.md` | Patcher | Global procedural skill library |
| `schema/style.md` | Patcher (learned) | PM preferences — tone, formatting, section order |

---

## Quick reference: what the Patcher must do on each ingest

```
1. Validate Tier 0 sections (always, even if no patch needed — no-op version bump)
2. Parse ingest source (email / invoice / bank transaction / letter)
3. Identify affected sections
4. For each affected section:
   a. Check for contradictions → _pending_review.md if found, stop
   b. Read schema/style.md for PM formatting preferences
   c. Write new content between @section anchors (tempfile → fsync → rename)
   d. Increment version=N on the anchor
   e. Add new [^footnote] definitions to provenance section only
5. Update frontmatter: last_patched, patcher_commit, open_issues_count
6. If tool_calls ≥ skill_extraction_threshold → run skill extraction
7. Append JSONL entry to _hermes_feedback.jsonl
8. If nudge_counter mod 15 == 0 → run periodic structure evaluation
9. git commit -m "ingest: {{INGEST_ID}} → {{HAUS_ID}} patches [{{sections}}]"
```

---

*BerlinHackBuena · BaC Hermes-Wiki Engine · Template v1.1.0 · 2026-04-25*
