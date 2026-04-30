# PropContext — Landing Page Brief (Loveable)

## Brand frame
- **Product:** PropContext — open-source living memory for property managers
- **Tagline:** *"Every email, invoice, and decision — distilled into one file your AI actually understands."*
- **Tone:** technical-confident, German-pragmatic, builder-friendly. Linear meets Supabase.
- **Palette:** off-white bg `#FAFAF7`, ink `#0A0A0A`, accent terracotta `#C2410C` (Berlin Altbau brick), muted sage `#84A98C` secondary. Mono accents for code/data.
- **Type:** Inter Tight (display), Inter (body), JetBrains Mono (code).

---

## Section 1 — Hero
Centered, generous whitespace, no carousel.

- Eyebrow chip: `OPEN SOURCE · MIT · BUILT IN BERLIN`
- H1: **The context layer for property management AI.**
- Sub: Email threads, invoices, bank tx, Stammdaten — compressed into one `building.md` per property. Your agent reads it in one shot. No RAG gymnastics.
- Primary CTA: `Star on GitHub →` (live star count)
- Secondary CTA: `Read the spec`
- Below CTAs: terminal block
  ```
  curl propcontext.dev/api/v1/buildings/charlottenburg-42/building.md
  ```
- Trust strip: "Used by [logo] · [logo] · 12 Berlin properties · 4,000+ docs ingested"

---

## Section 2 — Video (the demo)
Full-bleed dark band `#0A0A0A`, video centered with thick rounded frame.

- Header (white): **See it eat a property in 90 seconds.**
- Sub: Watch PropContext ingest a year of Hausverwaltung chaos and emit one file an LLM can reason over.
- Player: 16:9, custom dark chrome, autoplay-muted-loop poster, click-to-unmute. Terracotta progress bar.
- Below video: three pill chips — `Ingest` · `Compress` · `Serve` — clickable to scrub.

---

## Section 3 — The problem
Two columns. Left = messy. Right = clean.

- H2: **Property data lives in 9 places. Your AI can only see one.**
- Left: chaotic stack of cards labeled *Outlook thread*, *PDF invoice*, *DATEV export*, *WhatsApp from Hausmeister*, *stammdaten.json*, *WEG protocol*. Slight rotation, overlapping.
- Right: single clean `building.md` card, monospace, syntax-highlighted, scrollable preview.
- Caption: *One file. Versioned. Diffable. Auditable.*

---

## Section 4 — Benefits (value grid)
3×2 grid. Icon + headline + 2-line body. Hairline border, no shadow.

1. **One file per building** — Agent loads full context in single fetch. No vector DB, no chunk drift.
2. **German-law aware** — WEG, BauO Bln, BGB, BetrSichV, DSGVO obligations mapped out of the box.
3. **Self-improving schema** — Hermes loop watches what agents miss, proposes schema patches. Wiki gets smarter on its own.
4. **MCP-native** — Drops into Claude, Cursor, any MCP client. Org-scoped, OAuth via WorkOS.
5. **Diffable memory** — Every change is a git-style patch. Audit who changed what, when, why.
6. **Open source, self-hostable** — MIT. `docker compose up`. Data never leaves your infra.

---

## Section 5 — How it works
Horizontal 4-step flow, animated on scroll. Connecting line in terracotta.

1. **Ingest** — Email, PDF, JSON, bank CSV → raw store
2. **Extract** — LLM pulls structured facts using `WIKI_SCHEMA`
3. **Patch** — Validated diffs apply to `building.md` (controlled vocabulary enforced)
4. **Serve** — HTTP + MCP endpoints. Agent fetches, reasons, acts.

Below flow: code snippet tab-switcher
- `cURL` tab: GET request
- `MCP` tab: tool call
- `Python` tab: httpx client

Each ~6 lines, copy button top-right.

---

## Section 6 — Live example
Split screen, sticky on scroll.

- Left (sticky): rendered `building.md` for sample property — *Kantstraße 47, Charlottenburg*. Sections: Stammdaten · Mieter · Wartungsverträge · Offene Punkte · Decisions log.
- Right (scrolls): annotations explaining each section, what fed it, which schema rule applied.

---

## Section 7 — For whom
3 personas, equal cards.

- **Hausverwaltungen** — Stop re-explaining your portfolio to every new tool.
- **PropTech builders** — Skip the ingestion plumbing. Build the agent.
- **WEG-Beiräte** — One source of truth for the next Eigentümerversammlung.

---

## Section 8 — Open source / GitHub
Dark band, mirrors Section 2.

- H2: **Built in the open. Read every line.**
- Left: GitHub repo card — live stars, forks, last commit, license badge, contributor avatars.
- Right: terminal block
  ```
  git clone github.com/&lt;your-org&gt;/propcontext
  uv sync
  uv run fastapi dev app/main.py
  ```
- CTAs: `Star repo` · `Read AGENTS.md` · `Join Discord`

---

## Section 9 — FAQ
Accordion, 6 items.

- Why not just use RAG? — Property context is small, dense, relational. One file beats 1000 chunks.
- Does it speak German? — Schema, vocabulary, legal map are German-native. UI bilingual.
- Where does data live? — Your infra. Self-host in Docker. We never touch it.
- How is access controlled? — MCP org-scoping. Per-property allowlist. OAuth via WorkOS.
- What LLM does it use? — Bring your own. Default Claude, swappable.
- Production-ready? — Hackathon MVP today. Roadmap on GitHub.

---

## Section 10 — Footer CTA
- H2: **Give your AI a memory worth reading.**
- Buttons: `Star on GitHub` · `Book a demo`
- Footer rows: product · docs · GitHub · spec · Berlin office · MIT license · Impressum.

---

## Loveable-specific notes
- `framer-motion` for section-2 video reveal and section-5 flow line draw.
- CTAs as `<a>` not `<button>` where they navigate.
- `prefers-reduced-motion` guard required.
- Hero `building.md` snippet uses real repo content, not lorem.
- GitHub stars: fetch from `api.github.com/repos/...` client-side, cache 5min in localStorage.
- Video: host on Mux or Cloudflare Stream, not YouTube (no third-party chrome).
- Impressum + DSGVO cookie banner required for German audience.
