---
name: wiki-schema-principles
description: Architectural principles for the PropContext property wiki. Page-per-entity layout, four-op patcher contract, frontmatter discipline, alias-as-context principle. Loaded as the second half of the extractor system prompt. Keep short.
---

# Wiki Schema — Principles

PropContext's living-context wiki for German WEG property management follows the Karpathy `llm-wiki` pattern, adapted for event-driven ingestion. **Principles, not templates.** The LLM owns the body shape; the runtime owns the patch primitives and page index.

## 1. One property, one tree

Each Liegenschaft has its own subtree under `wiki/<LIE-id>/`. The runtime never crosses property boundaries.

## 2. Layered files

| File / dir | Owner | Purpose |
|---|---|---|
| `index.md` | runtime | Catalog of every page (regenerated each ingest) |
| `log.md` | LLM via `prepend_log` | Append-only chronological narrative |
| `building.md` | LLM | Synthesis / overview — the served headline |
| `entities/<ID>.md` | LLM | One page per canonical entity (DL, MIE, EIG, EH, HAUS, …) |
| `sources/<event_id>.md` | LLM | One page per ingested source |
| `topics/<slug>.md` | LLM | Issue / theme / project pages, created on demand |
| `lint_report.md` | runtime | Latest lint findings |

The LLM may invent new top-level dirs when a new kind of thing genuinely doesn't fit (`disputes/`, `meetings/`, `contracts/`). Reuse existing dirs first.

## 3. Frontmatter is the discovery layer

Every page begins with:

```yaml
---
name: <kebab-case>
description: <≤1024 chars; names entities, says when to read>
---
```

The next agent reads frontmatter only and decides whether to drill in. The runtime reads `name` + `description` to build `index.md`.

## 4. Four-op patcher contract

The LLM emits a `PatchPlan` with at most four kinds of op:

- `create_page(path, frontmatter, body)` — idempotent
- `upsert_section(path, heading, body)` — replace section body, append if missing
- `append_section(path, heading, line)` — append a line, create section if missing
- `prepend_log(line)` — prepend to `log.md`

The patcher is mechanical: zero LLM at apply time. Pure regex / line operations. Atomic write + git commit per event.

## 5. Provenance via footnotes

Every fact in a managed page carries a footnote pointing at its source: `[^EMAIL-12044]`. Footnote definitions live near the bottom of the page (heading at LLM's discretion — `## Provenance`, `## Sources`, …). The two-hop trace is `claim → footnote → sources/<event_id>.md → normalize/.../<event_id>.md`.

## 6. Wikilinks build the graph

Use `[[entities/DL-010.md]]` or short forms `[[DL-010]]` to cross-reference. The lint pass uses inbound-link counts to detect orphans.

## 7. Alias accumulation, not vocabulary control

There is no controlled vocabulary file. Variant references to the same entity (different names, email addresses, spellings) are **accumulated on the entity page** as the LLM encounters them. The wiki is its own dictionary.

The LLM uses context (`resolved_entities` from stammdaten + existing pages + located sections) to map mentions to canonical IDs — no hard validator.

## 8. Compactness

- Bullets > prose. Tables for repeating rows. Short paragraphs for synthesis only.
- Page soft target ≤30 KB; hard cap 50 KB triggers a split into child pages.
- Long timelines / chronological lists belong in `log.md` or a topic page, not in the entity page.

## 9. Human edits are sacred

Any page may contain a `# Human Notes` H1 followed by free-form human content. The patcher refuses to write past that boundary. The dedicated `PUT /api/v1/wiki/human-notes` endpoint owns that section.

## 10. Index, log, lint

- **index.md** is regenerated every ingest from page frontmatter. Don't patch it.
- **log.md** receives one line per event via `prepend_log`. Don't patch it directly.
- **lint_report.md** is rewritten each lint pass with orphan + missing-frontmatter findings.

## 11. Why this works

Karpathy's insight: maintenance is the bottleneck of a knowledge base, not capture. By making the patch primitives mechanical and the layout LLM-owned, we get a graph that compounds with every ingest. The human reads; the LLM writes; git remembers; the wiki keeps getting denser.
