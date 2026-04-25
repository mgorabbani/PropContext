# BerlinHackBuena

Property management runs on context. Every ticket, email, and owner question requires knowing a hundred things about one specific building: Who owns it, what the last assembly decided, whether the roof leak is open, who the heating contractor is.

Today, that context is scattered across ERPs, Gmail, Slack, Google Drive, scanned PDFs, and the head of the property manager who's been there twelve years. AI agents have to crawl all of it for every single task.

**The Goal**

Build an engine that produces a single Context Markdown File per property. That's a living, self-updating document containing every fact an AI agent needs to act. Dense, structured, traced to its source, surgically updated without destroying human edits. Think CLAUDE.md, but for a building, plus it writes itself.

**Why this is hard**

1. Schema alignment: "owner" is called Eigentümer, MietEig, Kontakt, or owner depending on the source system. You must resolve identities across ERPs.

2. Surgical updates: when an new email arrives you can't generate a whole new file. Regenerating the file destroys human edits and burns tokens. You must patch exactly the right section.

3. Signal vs. noise: 90% of emails are irrelevant. The engine must judge what belongs in the context and what doesn't.

## Overview

BerlinHackBuena is an early-stage hackathon project focused on turning scattered business context into usable, searchable, and explainable information. The repository currently contains a sample data set under `hackathon/` with documents such as invoices, emails, letters, bank data, master data, and incremental updates.

The goal is to build a system that can ingest these sources, extract relevant facts, preserve provenance, and help users answer operational questions with the right context.

## Project Goals

- Ingest structured and unstructured business documents.
- Extract entities, dates, amounts, relationships, and document metadata.
- Link information across emails, invoices, bank records, letters, and master data.
- Provide a context layer that supports reliable search, retrieval, and question answering.
- Keep source references available so answers can be traced back to original documents.

## Initial Ideas

- Document parsing pipeline for PDFs, emails, and tabular files.
- Normalized data model for contacts, companies, invoices, payments, messages, and events.

Possible first milestones:

1. Add a document ingestion script.
2. Extract metadata....

## Demo

```bash
# 1. install
uv sync

# 2. bootstrap a wiki skeleton from stammdaten and index it
uv run python -m app.tools.bootstrap_wiki

# 3. start the API + SSE live view
APP_WEBHOOK_HMAC_SECRET=demo uv run fastapi run app/main.py
#   -> http://localhost:8000/         live pulses (EventSource)
#   -> http://localhost:8000/api/v1/properties/LIE-001  current building.md
#   -> http://localhost:8000/api/v1/events                SSE stream

# 4. replay one day of deltas (in another shell)
APP_WEBHOOK_HMAC_SECRET=demo \
  uv run python -m app.tools.replay --day 1 --rate 1.0

# 5. backfill 2024-2025 archive (cost-capped)
APP_WEBHOOK_HMAC_SECRET=demo \
  uv run python -m app.tools.backfill --limit 200 --rate 2.0

# 6. reconciliation report
uv run python -m app.tools.reconcile --write-wiki
```

`AGENTS.md` (symlinked as `CLAUDE.md`) is the source of truth for code style and pipeline architecture. `IMPLEMENTATION_PLAN.md` traces the phased build.

## Tests

```bash
uv run pytest                 # full suite
uv run pytest tests/e2e -q    # end-to-end day-01 replay
uv run ruff check . && uv run ty check
```

## License

License not specified yet.
