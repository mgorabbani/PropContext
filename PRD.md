# Product Requirements Document: Living Context Wiki for Property Operations

## 1. Summary

Build an agentic context engine that turns scattered property-management documents into a living, source-backed, hierarchical wiki. The system ingests files such as emails, invoices, letters, bank records, master data, and incremental updates; extracts operational facts; links them to the right property, people, vendors, issues, and events; and surgically updates context markdown files in near real time.

The core output is not a chat answer or a one-time summary. It is a maintained context layer that other agents can use before acting.

The project combines:

- A Karpathy-style LLM wiki: persistent markdown pages that accumulate knowledge over time.
- A hierarchical file index: every source file is represented in a navigable document tree.
- A living property memory: one high-density context page per building.
- An agent update loop: new inputs trigger classification, extraction, linking, and precise markdown patches.

## 2. Problem

Property managers repeatedly reconstruct context from scattered systems. A single tenant email may require checking prior emails, invoices, letters, master data, bank records, and old decisions. Most AI systems retrieve snippets at query time, which means they rediscover the same context again and again.

The system should instead compile raw operational documents into a durable, maintained context layer.

Key challenges:

- Schema alignment: the same entity can appear under different names, IDs, languages, and file types.
- Signal filtering: many emails and documents do not change operational context.
- Surgical updates: new data must update only the relevant section without destroying human edits.
- Provenance: every important claim must trace back to source files.
- Real-time updates: new emails or incremental drops should update context automatically.
- Hierarchical navigation: agents need both high-level summaries and drill-down access to source-level detail.

## 3. Goals

- Create a persistent wiki under a generated context directory.
- Build one living `building.md`-style context file per property.
- Maintain a hierarchical index of source files and derived wiki pages.
- Ingest and process existing files under `data/`.
- Detect new files, especially emails and incremental updates, and update context automatically.
- Extract facts, entities, relationships, timelines, open issues, obligations, invoices, risks, and tasks.
- Preserve source provenance for every material fact.
- Support context packs that retrieve the right pages and source snippets for an agent task.
- Avoid full-file regeneration when updating property context.

## 4. Non-Goals

- Replacing the property management ERP.
- Sending emails or making external payments in the MVP.
- Providing legal, accounting, or compliance decisions without human review.
- Building a full production permission model during the hackathon MVP.
- Perfect entity resolution across all possible external systems.
- Fully autonomous action without auditable context and approval gates.

## 5. Target Users

- Property managers who need fast, reliable context before responding to tenants, owners, vendors, or accountants.
- Operations leads who need daily briefings on what changed and what needs attention.
- AI agents that need compact, source-backed context before drafting replies, approving workflows, or escalating issues.
- Hackathon judges evaluating whether the system can convert messy property data into living operational memory.

## 6. User Stories

### Property Manager

- As a property manager, I want to ask what changed for a building today so I can prioritize work.
- As a property manager, I want a single building context file so I do not need to search all source systems manually.
- As a property manager, I want facts to include source references so I can verify them quickly.
- As a property manager, I want irrelevant emails ignored or marked as low-signal so the context stays clean.
- As a property manager, I want human edits in the context file preserved when new data arrives.

### AI Agent

- As an agent, I want to retrieve a compact context pack for a task so I can act without loading the whole corpus.
- As an agent, I want the latest property facts, open issues, and timeline before drafting a tenant response.
- As an agent, I want to know which facts are stale, contradicted, or low confidence.
- As an agent, I want stable page paths and source IDs so I can cite and update context reliably.

### System Operator

- As an operator, I want new files in `data/incremental/` to trigger ingestion automatically.
- As an operator, I want a log of every wiki update, including source file, extracted facts, pages touched, and confidence.
- As an operator, I want review queues for ambiguous matches and risky updates.

## 7. Core Product Concept

### 7.1 Raw Sources

The raw source layer is immutable input. For this repo, initial sources live under:

- `data/emails/`
- `data/rechnungen/`
- `data/briefe/`
- `data/bank/`
- `data/stammdaten/`
- `data/incremental/`

Source files should never be edited by the agent.

### 7.2 Hierarchical Source Index

The system maintains a Wikipedia-like source index that mirrors and enriches the file tree.

Example:

```text
context/
  sources/
    index.md
    emails/
      index.md
      2025-04/
        index.md
        20250411_101500_EMAIL-01234.md
    rechnungen/
      index.md
      2025-04/
        index.md
        20250428_DL-001_INV-00130.md
```

Each source page contains:

- canonical source ID
- original file path
- file type
- date received or created
- extracted metadata
- short summary
- linked entities
- linked properties
- linked issues or events
- processing status
- confidence

### 7.3 Living Property Wiki

The property wiki contains synthesized operational pages. It is the main context layer agents should read.

Example:

```text
context/
  properties/
    index.md
    BUILDING-001/
      building.md
      timeline.md
      open-issues.md
      invoices.md
      contacts.md
      decisions.md
      risks.md
      source-map.md
```

The `building.md` page is the dense, high-level memory file. Supporting pages hold detail that would make the main page too large.

### 7.4 Context Packs

For every user or agent task, the system produces a compact context pack.

Example:

```json
{
  "task": "Draft a response to the tenant about the heating issue",
  "property_id": "BUILDING-001",
  "relevant_pages": [
    "context/properties/BUILDING-001/building.md",
    "context/properties/BUILDING-001/open-issues.md",
    "context/properties/BUILDING-001/timeline.md"
  ],
  "source_refs": [
    "EMAIL-03152",
    "INV-00130"
  ],
  "constraints": [
    "Heating issue is still marked open",
    "Contractor response is pending",
    "Do not claim repair completion without confirmation"
  ],
  "open_questions": [
    "Has the contractor visited after the latest tenant complaint?"
  ]
}
```

## 8. Functional Requirements

### 8.1 Ingestion

The system must ingest:

- `.eml` email files
- PDF invoices
- PDF or text letters
- CSV, JSON, or spreadsheet-like master data where available
- incremental update folders

For each source, the system must:

- assign a stable source ID
- parse available text and metadata
- extract dates, senders, recipients, subjects, invoice numbers, amounts, vendors, buildings, tenants, owners, and issue references
- classify document type
- detect duplicate or near-duplicate files
- write or update a source page
- append an ingest event to `context/log.md`

### 8.2 Hierarchical Wikipedia Indexing

The system must maintain markdown index pages at every major hierarchy level.

Each `index.md` must include:

- child pages
- one-line summaries
- date range
- source count
- high-signal changes
- unresolved processing issues

The top-level index must let an agent quickly locate:

- all properties
- all source categories
- recent updates
- open issues
- pending review items
- stale or contradictory facts

### 8.3 Entity Resolution

The system must identify and link:

- properties/buildings
- owners
- tenants
- contractors/vendors
- invoices
- payments
- emails and threads
- repairs or maintenance issues
- legal or compliance events
- decisions and approvals

Entity resolution should combine:

- exact IDs from master data
- names and aliases
- email addresses
- addresses
- invoice references
- temporal proximity
- existing wiki links
- LLM-assisted matching with confidence

Ambiguous matches must be routed to a review queue instead of silently updating high-confidence context.

### 8.4 Signal vs. Noise Filtering

Every ingested item must receive a signal classification:

- `context_update`: changes a durable property fact
- `task_update`: creates, updates, or resolves work
- `financial_update`: affects invoices, payments, budget, or approval
- `risk_update`: affects legal, safety, compliance, tenant satisfaction, or escalation risk
- `reference_only`: useful as source detail but not worth adding to `building.md`
- `noise`: duplicate, irrelevant, automated, or low-value

Noise should still be logged and searchable, but should not pollute high-level property context.

### 8.5 Surgical Markdown Updates

The system must update generated markdown pages without rewriting entire files whenever possible.

Requirements:

- preserve human edits outside managed blocks
- use stable section headings and anchors
- update only the affected section
- retain provenance footnotes or source links
- mark changed facts with `updated_at`
- mark superseded facts instead of deleting important history
- write a patch summary to the log

Recommended convention:

```md
<!-- managed:open-issues:start -->
...
<!-- managed:open-issues:end -->
```

Human-owned sections should be clearly separated:

```md
<!-- human-notes:start -->
...
<!-- human-notes:end -->
```

### 8.6 Real-Time Context Updates

The system must support automatic updates when new source data appears.

MVP trigger:

- file watcher on `data/incremental/`

Future triggers:

- Gmail or IMAP webhook/polling
- Slack or Teams events
- Drive or SharePoint file updates
- ERP export drops
- bank feed imports

When a new email arrives, the system should:

1. Parse the email.
2. Identify property, people, thread, issue, and attachments.
3. Classify signal level.
4. Update the source index.
5. Update affected property pages.
6. Update open tasks, timeline, and building summary if warranted.
7. Log every page touched.
8. Add ambiguous or risky changes to review.

### 8.7 Timeline Intelligence

Each property must have a timeline page that records important events:

- tenant complaints
- owner decisions
- contractor responses
- invoice receipt and approval
- payment events
- legal or compliance letters
- maintenance visits
- unresolved follow-ups

Timeline entries must include:

- event date
- event type
- summary
- linked entities
- source references
- confidence

### 8.8 Open Issues and Tasks

Each property must maintain an open-issues page.

Issue records should include:

- issue ID
- title
- status
- priority
- property
- affected units or tenants
- responsible party
- next action
- due date if known
- linked timeline events
- linked sources
- confidence

The system should detect when new messages refer to existing issues rather than creating duplicates.

### 8.9 Provenance and Auditability

Every material claim in property context must be traceable to one or more sources.

The system must support:

- source IDs
- source file paths
- extracted snippets where legally and practically appropriate
- page-level source maps
- update logs
- confidence labels
- contradiction flags

Agents must avoid making recommendations from unsupported facts.

### 8.10 Query and Context Retrieval

The system must expose a way to retrieve context for an agent task.

MVP interface:

- CLI command that returns a markdown or JSON context pack

Example:

```bash
context pack --property BUILDING-001 --task "reply to heating complaint"
```

The retrieval should combine:

- hierarchical index lookup
- keyword search
- semantic search where available
- graph links between pages
- recency weighting
- issue status
- source confidence

## 9. Data Model

### 9.1 Source Document

```ts
type SourceDocument = {
  id: string
  path: string
  type: "email" | "invoice" | "letter" | "bank" | "master_data" | "other"
  receivedAt?: string
  documentDate?: string
  title: string
  summary: string
  entities: string[]
  properties: string[]
  extractedFacts: string[]
  signalClass: string
  confidence: "low" | "medium" | "high"
  status: "new" | "processed" | "needs_review" | "duplicate" | "noise"
}
```

### 9.2 Context Page

```ts
type ContextPage = {
  id: string
  path: string
  title: string
  pageType: "property" | "entity" | "issue" | "timeline" | "source_index" | "briefing"
  summary: string
  tags: string[]
  links: string[]
  sources: string[]
  updatedAt: string
  confidence: "low" | "medium" | "high"
  status: "active" | "stale" | "superseded" | "needs_review"
}
```

### 9.3 Fact

```ts
type Fact = {
  id: string
  subject: string
  predicate: string
  object: string
  propertyId?: string
  sourceIds: string[]
  firstSeenAt: string
  lastConfirmedAt: string
  confidence: "low" | "medium" | "high"
  status: "active" | "stale" | "contradicted" | "superseded"
}
```

## 10. Agent Roles

### 10.1 Archivist Agent

Owns ingestion, indexing, source summaries, and wiki hygiene.

### 10.2 Context Router Agent

Builds context packs for user or worker-agent tasks.

### 10.3 Entity Resolver Agent

Links people, vendors, buildings, invoices, payments, and issues across messy sources.

### 10.4 Noise Filter Agent

Classifies whether a source should update durable context, create a task, remain reference-only, or be treated as noise.

### 10.5 Critic Agent

Checks contradictions, stale facts, unsupported claims, duplicate issues, and missing provenance.

### 10.6 Briefing Agent

Produces daily or weekly operational summaries: what changed, what needs action, what is risky, and what is waiting on someone else.

## 11. User Experience

### 11.1 MVP CLI

The first usable interface should be a CLI:

```bash
context ingest data/
context watch data/incremental/
context index
context pack --property BUILDING-001 --task "What changed today?"
context brief --date today
context lint
```

### 11.2 Markdown Wiki

The generated wiki should be readable in any editor and especially useful in Obsidian or similar markdown tools.

Pages should use:

- stable file paths
- YAML frontmatter
- clear headings
- wikilinks where practical
- source footnotes or source link blocks
- concise summaries before details

### 11.3 Review Queue

Ambiguous or risky changes should be written to:

```text
context/review/
  index.md
  pending-entity-matches.md
  pending-context-updates.md
  contradictions.md
```

## 12. MVP Scope

The hackathon MVP should prove the core loop:

1. Ingest a representative subset of `data/`.
2. Generate source pages and hierarchical indexes.
3. Identify at least one property/building from master data or document references.
4. Create a living `building.md` page.
5. Process a new email from `data/incremental/`.
6. Classify the email as signal or noise.
7. Surgically update the relevant property page, timeline, and open issue.
8. Generate a source-backed context pack for a task.
9. Produce an update log that shows what changed and why.

MVP success demo:

- Drop a new tenant email into `data/incremental/day-XX/`.
- The watcher ingests it automatically.
- The system links it to the correct property and issue.
- `building.md`, `timeline.md`, and `open-issues.md` are patched.
- `context/log.md` records the update.
- A context pack explains what an AI responder needs to know.

## 13. Stretch Scope

- Gmail or IMAP connector for live email.
- Attachment extraction and linking.
- Vector search over source pages and wiki pages.
- UI for browsing properties, issues, sources, and review queue.
- Human approval workflow for risky updates.
- Daily briefing generation.
- Building health score.
- Markdown AST-based patching instead of text block replacement.
- Agent skill extraction for recurring workflows.
- Multi-property portfolio dashboard.
- MCP server exposing context tools to external agents.

## 14. Success Metrics

### Product Metrics

- Percentage of new high-signal emails correctly linked to a property.
- Percentage of context updates with source provenance.
- Reduction in time needed to answer “what happened with this issue?”
- Number of duplicate issues avoided.
- Number of stale or contradictory facts detected.

### Technical Metrics

- Ingestion latency for new files.
- Patch size compared with full page size.
- Entity match confidence and review rate.
- Retrieval precision for context packs.
- Index freshness after file changes.

### Demo Metrics

- New email processed within 30 seconds.
- At least three wiki pages updated from one meaningful source.
- At least one noisy source ignored but logged.
- Every demo answer cites source IDs.

## 15. Architecture

```text
Raw Data
  |
  v
File Watcher / Batch Ingest
  |
  v
Parsers
  |
  v
Document Classifier + Noise Filter
  |
  v
Entity Resolver + Fact Extractor
  |
  v
Source Index + Fact Store
  |
  v
Wiki Patch Engine
  |
  v
Property Wiki + Context Packs
```

Recommended local stack:

- Runtime: Python or TypeScript
- Storage: SQLite for metadata, markdown for durable context
- Search: BM25 first, vector search optional
- Parsing: email parser for `.eml`, PDF text extraction for invoices and letters
- Markdown updates: managed blocks for MVP, AST patching for stretch
- Watcher: filesystem watcher on `data/incremental/`
- Agent interface: CLI first, MCP server later

## 16. Suggested Directory Structure

```text
.
  PRD.md
  data/
  context/
    index.md
    log.md
    review/
    sources/
    properties/
    entities/
    issues/
    briefings/
  src/
    ingest/
    parse/
    classify/
    resolve/
    index/
    patch/
    retrieve/
    cli/
  tests/
```

Generated files under `context/` should be excluded from git unless the team decides to preserve sample outputs for the demo.

## 17. Risks and Mitigations

| Risk | Mitigation |
| --- | --- |
| Entity resolution links a source to the wrong property | Use confidence thresholds and review queue |
| Generated wiki becomes noisy | Enforce signal classification before property updates |
| Human edits are overwritten | Use managed blocks and patch logs |
| Facts cannot be traced | Require source IDs for material claims |
| Context becomes stale | Run periodic lint and contradiction checks |
| Parsing PDFs is unreliable | Store confidence and keep source links visible |
| Real-time integrations are too large for MVP | Start with filesystem watcher over `data/incremental/` |

## 18. Open Questions

- What is the canonical property/building identifier in the available data?
- Which source type has the strongest property linkage: master data, invoices, emails, or letters?
- Should the MVP generate one property page or multiple pages for all detected properties?
- Which LLM provider and model should be used for extraction in the hackathon environment?
- Should generated `context/` output be committed for judging, or regenerated during the demo?
- What level of human review is required before a fact changes `building.md`?

## 19. Acceptance Criteria

The MVP is complete when:

- `context ingest data/` creates a hierarchical source index.
- At least one property has a generated `building.md`.
- At least one property has generated `timeline.md` and `open-issues.md`.
- A new `.eml` file placed in an incremental folder triggers automatic processing.
- The system classifies the new email as signal, reference-only, or noise.
- A meaningful email updates only relevant managed sections.
- Update logs list source ID, pages touched, extracted facts, and confidence.
- A context pack can be generated for a task and includes source-backed constraints.
- Unsupported or ambiguous claims are routed to review rather than silently written as facts.

