# Wiki Schema — BerlinHackBuena

Concrete schema for the building-context wiki. Three layers: directory layout, frontmatter contract, anchor blocks per file type. Plus write rules, wikilink convention, and health-score formula.

This is the contract every Patcher / Linter / Extractor agent must obey.

---

## 1. Directory layout

```
wiki/
├── index.md                          # global catalog (all properties)
├── LIE-001/
│   ├── index.md                      # Liegenschaft entry — top of hierarchy
│   ├── log.md                        # append-only event log
│   ├── open_issues.md                # rolling task list across whole property
│   ├── _pending_review.md            # contradictions waiting for PM
│   ├── HAUS-12/
│   │   ├── index.md                  # ★ THE building.md (demo headliner)
│   │   ├── EH-001.md
│   │   ├── EH-002.md
│   │   └── ...
│   ├── HAUS-13/
│   │   └── ...
│   ├── HAUS-14/
│   │   └── ...
│   ├── eigentuemer/
│   │   ├── EIG-001.md … EIG-035.md
│   ├── mieter/
│   │   ├── MIE-001.md … MIE-026.md
│   └── dienstleister/
│       ├── DL-001.md … DL-016.md
└── _versions/                        # patch history snapshots (optional)
```

---

## 2. Frontmatter contract (every wiki file)

```yaml
---
id: HAUS-12
type: gebaeude                        # liegenschaft | gebaeude | einheit | eigentuemer | mieter | dienstleister
parent: LIE-001
children: [EH-001, EH-002, ..., EH-019]
created_at: 2026-04-25T10:00:00Z
last_patched: 2026-04-25T14:32:11Z
patcher_commit: a3f2c19
schema_version: 1
health_score: 0.78                    # derived, for Dataview dashboards
open_issues_count: 3
tags: [building, weg]
---
```

Type-specific extra fields (additive):

- **gebaeude:** `address`, `units_count`, `qm_total`, `baujahr`
- **einheiten:** `haus`, `we_nr`, `qm`, `zimmer`, `miteigentumsanteil`, `current_tenant`, `current_owner`
- **eigentuemer:** `name`, `email`, `selbstnutzer`, `beirat`, `sev_mandat`, `iban`, `units`
- **mieter:** `name`, `email`, `unit`, `kaltmiete`, `nk`, `kaution`, `mietbeginn`, `mietende`, `iban`
- **dienstleister:** `firma`, `kategorie`, `iban`, `ust_id`, `stundensatz`

---

## 3. Anchor blocks per file type

Convention: `<!-- @section:KEY version=N -->` ... `<!-- @end:KEY -->`. Patcher rewrites only between matching markers. Outside = human-owned.

### `LIE-001/index.md` — Liegenschaft

```markdown
---
id: LIE-001
type: liegenschaft
schema_version: 1
---

# WEG Immanuelkirchstraße 26, 10405 Berlin

<!-- @section:summary version=1 -->
1 Verwalter, 3 Häuser, 52 Einheiten, 35 Eigentümer, 26 Mieter, 16 Dienstleister.
<!-- @end:summary -->

<!-- @section:bank_accounts version=1 -->
- **WEG-Konto:** DE02 1001 0010 0123 4567 89 (Postbank) — Betrieb
- **Rücklage:** DE12 1203 0000 0098 7654 32 (BayernLB)
- **Verwalter:** DE89 3704 0044 0532 0130 00 (Commerzbank)
<!-- @end:bank_accounts -->

<!-- @section:buildings version=1 -->
- [[HAUS-12]] — Vorderhaus, 19 EH
- [[HAUS-13]] — Seitenflügel, 17 EH
- [[HAUS-14]] — Hinterhaus, 16 EH
<!-- @end:buildings -->

<!-- @section:procedural_memory version=1 -->
<!-- skills extracted by Linter (Hermes step 3-4) -->
<!-- @end:procedural_memory -->

<!-- @section:risk_profile version=1 -->
<!-- @end:risk_profile -->

## Notes (human-owned, never patched)
<!-- free-form area below — Patcher must not touch -->
```

### `LIE-001/HAUS-12/index.md` — the headline building.md

```markdown
---
id: HAUS-12
type: gebaeude
parent: LIE-001
address: Immanuelkirchstraße 26, Vorderhaus
units_count: 19
schema_version: 1
health_score: 0.78
last_patched: 2026-04-25T14:32:11Z
---

# HAUS-12 — Vorderhaus

<!-- @section:core_metadata version=1 -->
- **Adresse:** Immanuelkirchstraße 26, Vorderhaus, 10405 Berlin
- **Baujahr:** 1908
- **Einheiten:** 19 (EH-001 … EH-019)
- **Hausmeister:** [[DL-003]]
- **Aufzug:** keiner
<!-- @end:core_metadata -->

<!-- @section:physical_state version=1 -->
- **Heizung:** Gaszentralheizung Buderus GB 162, installiert 2019 [^INV-00018]
- **Boiler letzte Wartung:** 2025-11-04 [^INV-01421]
- **Dach:** saniert 2022 [^LTR-0042]
- **Keybox:** 5543 [Updated 2024-03-10 via [^EMAIL-02301]]
- **Risiko:** alternde Steigleitungen, Reparatur 2024 abgewiesen [^EMAIL-04421]
<!-- @end:physical_state -->

<!-- @section:procedural_memory version=2 -->
- **Heizungsausfall nach 18 Uhr:** Erst [[DL-007]] (Notdienst, +49 30 555-0123), nicht [[DL-003]] (Hausmeister hat keinen Schlüssel zum Heizungsraum). Extracted 2026-04-22 after 7-step trajectory.
- **Wasserschaden Notfall:** Foto + Mieter-IBAN sofort an Versicherung [[DL-011]]. Extracted 2026-03-15.
<!-- @end:procedural_memory -->

<!-- @section:open_issues version=5 -->
- 🔴 **Heizung EH-014** — kein Warmwasser seit 2026-04-23. Kontraktor [[DL-007]] kontaktiert 2026-04-24. [^EMAIL-12044]
- 🟡 **Mieterhöhung MIE-019** — Widerspruch eingegangen, Frist 2026-05-15. [^LTR-0128]
- 🟢 **BKA 2024** — versendet 2025-03-12, 2 Rückfragen offen. [^LTR-0089]
<!-- @end:open_issues -->

<!-- @section:recent_events version=12 -->
| Datum | Typ | Zusammenfassung | Quelle |
|---|---|---|---|
| 2026-04-25 | email | Heizungsbeschwerde EH-014 | [^EMAIL-12044] |
| 2026-04-23 | invoice | Boiler-Service DL-007 €380 | [^INV-02103] |
| 2026-04-21 | bank | Hausgeld EIG-014 €412 eingegangen | [^TX-1604] |
<!-- @end:recent_events -->

<!-- @section:contractors_active version=1 -->
- Hausmeister: [[DL-003]]
- Heizung-Notdienst: [[DL-007]]
- Aufzug: n/a
- Reinigung: [[DL-005]]
- Versicherung: [[DL-011]]
<!-- @end:contractors_active -->

<!-- @section:provenance version=1 -->
[^EMAIL-12044]: `normalize/eml/2026-04/EMAIL-12044.md` → `raw/emails/2026-04-25/...eml`
[^INV-02103]: `normalize/pdf/2026-04/INV-02103.md` → `raw/rechnungen/2026-04/...pdf`
[^INV-00018]: `normalize/pdf/2019-03/INV-00018.md`
[^INV-01421]: `normalize/pdf/2025-11/INV-01421.md`
[^LTR-0042]: `normalize/pdf/2022-08/LTR-0042.md`
[^LTR-0089]: `normalize/pdf/2025-03/LTR-0089.md`
[^LTR-0128]: `normalize/pdf/2026-04/LTR-0128.md`
[^EMAIL-02301]: `normalize/eml/2024-03/EMAIL-02301.md`
[^EMAIL-04421]: `normalize/eml/2025-09/EMAIL-04421.md`
[^TX-1604]: `bank_index.csv:1604`
<!-- @end:provenance -->

## PM Notes (human-owned)
<!-- below this line never touched by agents -->
```

### `LIE-001/HAUS-12/EH-014.md` — Einheit (apartment)

```markdown
---
id: EH-014
type: einheit
parent: HAUS-12
we_nr: 14
qm: 67.4
zimmer: 2.5
miteigentumsanteil: 18.7
current_tenant: MIE-014
current_owner: EIG-009
---

# EH-014 — 2. OG links

<!-- @section:unit_facts version=1 -->
- **Größe:** 67.4 m², 2.5 Zimmer
- **MEA:** 18.7
- **Lage:** 2. OG links, Vorderhaus
<!-- @end:unit_facts -->

<!-- @section:current_tenant version=2 -->
- [[MIE-014]] — Anna Müller, seit 2023-08-01
- Kaltmiete: 894,00 €
- NK-Vorauszahlung: 180,00 €
- Kaution: 2682,00 € (auf Kautionskonto)
<!-- @end:current_tenant -->

<!-- @section:current_owner version=1 -->
- [[EIG-009]] — Klaus Schmidt, Selbstnutzer: nein
<!-- @end:current_owner -->

<!-- @section:history version=4 -->
- 2023-08-01 — Mietbeginn [[MIE-014]] [^LTR-0021]
- 2024-11 — Heizungsproblem (gelöst) [^EMAIL-08812]
- 2026-04-23 — Heizungsproblem erneut, offen [^EMAIL-12044]
<!-- @end:history -->

<!-- @section:provenance version=1 -->
[^LTR-0021]: ...
[^EMAIL-08812]: ...
[^EMAIL-12044]: ...
<!-- @end:provenance -->
```

### `LIE-001/eigentuemer/EIG-014.md`

```markdown
---
id: EIG-014
type: eigentuemer
name: Maria Weber
email: m.weber@example.de
selbstnutzer: false
beirat: true
sev_mandat: true
iban: DE12 ...
units: [EH-014, EH-027]
---

# EIG-014 — Maria Weber

<!-- @section:contact version=1 -->
- E-Mail: m.weber@example.de
- Telefon: +49 30 555-1234
- Anschrift: ...
<!-- @end:contact -->

<!-- @section:units_owned version=1 -->
- [[EH-014]] (HAUS-12) — vermietet an [[MIE-014]]
- [[EH-027]] (HAUS-13) — Selbstnutzung: nein, leer
<!-- @end:units_owned -->

<!-- @section:roles version=1 -->
- Beirat: ja
- SEV-Mandat: ja
<!-- @end:roles -->

<!-- @section:payment_history version=8 -->
- Hausgeld 2026-04: €412 (pünktlich) [^TX-1604]
- Hausgeld 2026-03: €412 (pünktlich) [^TX-1432]
- Sonderumlage Dach 2024: €1.247 (verspätet 14 Tage) [^TX-0822]
<!-- @end:payment_history -->

<!-- @section:correspondence_summary version=3 -->
- Stimmt typischerweise konservativ in ETV ab.
- Reagiert auf E-Mails innerhalb 24h.
- Bevorzugt schriftlich (kein Telefon).
<!-- @end:correspondence_summary -->

<!-- @section:open_items version=1 -->
- offen: Antwort auf Anfrage Steigleitungen-Sanierung (2026-04-18) [^EMAIL-11801]
<!-- @end:open_items -->

<!-- @section:provenance version=1 -->
[^TX-1604]: bank_index.csv:1604
[^TX-1432]: bank_index.csv:1432
[^TX-0822]: bank_index.csv:822
[^EMAIL-11801]: normalize/eml/2026-04/EMAIL-11801.md
<!-- @end:provenance -->
```

### `LIE-001/mieter/MIE-014.md`

```markdown
---
id: MIE-014
type: mieter
name: Anna Müller
email: anna.mueller@example.de
unit: EH-014
kaltmiete: 894.00
mietbeginn: 2023-08-01
mietende: null
iban: DE12 ...
---

# MIE-014 — Anna Müller

<!-- @section:contact version=1 -->
<!-- @end:contact -->

<!-- @section:tenancy version=1 -->
- Einheit: [[EH-014]] in [[HAUS-12]]
- Mietvertrag: 2023-08-01 — unbefristet
- Kaltmiete: 894,00 €, NK 180,00 €
- Kaution: 2682,00 € auf Kautionskonto, vollständig hinterlegt 2023-08-15 [^TX-0212]
<!-- @end:tenancy -->

<!-- @section:payment_history version=12 -->
- 2026-04-01: 1074,00 € (pünktlich) [^TX-1598]
- 2026-03-01: 1074,00 € (pünktlich) [^TX-1421]
- 2024-02: -3 Tage verspätet
<!-- @end:payment_history -->

<!-- @section:contact_history version=6 -->
- 2026-04-25: Heizungsausfall gemeldet [^EMAIL-12044]
- 2024-11-15: Heizungsausfall (gelöst innerhalb 18h) [^EMAIL-08812]
- 2024-03-02: Schlüsselverlust gemeldet [^EMAIL-02301]
<!-- @end:contact_history -->

<!-- @section:open_items version=1 -->
- 🔴 Heizungsausfall offen seit 2026-04-23
<!-- @end:open_items -->

<!-- @section:provenance version=1 -->
<!-- @end:provenance -->
```

### `LIE-001/dienstleister/DL-007.md`

```markdown
---
id: DL-007
type: dienstleister
firma: Heizungstechnik Berlin GmbH
kategorie: heizung
iban: DE12 ...
ust_id: DE123456789
stundensatz: 95.00
---

# DL-007 — Heizungstechnik Berlin GmbH

<!-- @section:services version=1 -->
- Heizungswartung jährlich
- Notdienst 24/7 (+49 30 555-0123)
- Boiler, Steigleitungen, Thermostate
<!-- @end:services -->

<!-- @section:contracts version=1 -->
- Wartungsvertrag HAUS-12: jährlich, €1200/Jahr
- Notdienst: pauschal €180 + Material
<!-- @end:contracts -->

<!-- @section:recent_invoices version=4 -->
| Datum | INV | Betrag | Status |
|---|---|---|---|
| 2026-04-24 | INV-02103 | €380,00 | bezahlt 2026-04-26 [^TX-1612] |
| 2025-11-04 | INV-01421 | €1.247,00 | bezahlt [^TX-1389] |
<!-- @end:recent_invoices -->

<!-- @section:performance_notes version=2 -->
- Reaktionszeit Notdienst: typisch 2-4h, einmal 18h (2024-11) [^EMAIL-08812]
- Rechnungen meist binnen 7 Tagen, manchmal IBAN-Tippfehler (2x in 2025) [^bank_anomaly_log]
<!-- @end:performance_notes -->

<!-- @section:provenance version=1 -->
<!-- @end:provenance -->
```

### `LIE-001/log.md` — append-only event log

Karpathy convention: every entry starts `## [YYYY-MM-DD HH:MM:SS]` so `grep "^## \[" log.md | tail -5` works.

```markdown
# Event Log — LIE-001

## [2026-04-25 14:32:11] ingest | EMAIL-12044
- source: gmail
- entities: [MIE-014, EH-014, HAUS-12, DL-007]
- patches:
  - HAUS-12/index.md § open_issues v4 → v5
  - HAUS-12/EH-014.md § history v3 → v4
  - mieter/MIE-014.md § contact_history v5 → v6
  - mieter/MIE-014.md § open_items v0 → v1
- complexity: 3 tool calls (below threshold)
- commit: a3f2c19

## [2026-04-25 11:08:42] ingest | INV-02103
- source: drive
- entities: [DL-007, HAUS-12]
- patches:
  - dienstleister/DL-007.md § recent_invoices v3 → v4
  - HAUS-12/index.md § recent_events v11 → v12
- commit: 7b21cce

## [2026-04-22 09:14:03] skill_extracted
- trigger: 7-step trajectory on EMAIL-11944 (Heizung after-hours)
- skill: "Heizungsausfall nach 18 Uhr → DL-007 zuerst"
- written to: schema/skills.md, HAUS-12 § procedural_memory
- commit: 1ee8f30

## [2026-04-20 16:00:00] lint | contradiction_flagged
- HAUS-12 § physical_state says "Boiler-Wartung 2025-11-04"
- but new claim from EMAIL-11801 says "Boiler hatte keine Wartung 2025"
- written to: _pending_review.md
- not auto-resolved
```

### `schema/skills.md` — procedural memory (Hermes step 3-4)

```markdown
# Procedural Skills

<!-- @skill:heating-emergency-after-hours version=2 -->
**When:** Heizungsausfall ≥18:00 oder Wochenende, jedes HAUS
**Steps:**
1. DL-007 Notdienst rufen (+49 30 555-0123) — NICHT Hausmeister DL-003
2. Mieter-Kontaktdaten + EH-Nummer + Hauszugang (Keybox) bereithalten
3. Wenn keine Antwort innerhalb 30min: Backup [[DL-009]]
4. Foto-Doku verlangen für Versicherung [[DL-011]]
**Source trajectories:** EMAIL-11944 (2026-04-22), EMAIL-08812 (2024-11-15)
**Confidence:** 0.92 (2 successful resolutions)
<!-- @end:heating-emergency-after-hours -->

<!-- @skill:water-damage-emergency version=1 -->
...
<!-- @end:water-damage-emergency -->
```

### `schema/style.md` — user-modeling (Hermes step 6)

```markdown
# Learned PM Preferences

<!-- @pref:section_order version=3 -->
HAUS index.md anchors should appear in this order (PM moves them):
1. core_metadata
2. open_issues          # PM consistently moves to top
3. physical_state
4. procedural_memory
5. recent_events
6. contractors_active
7. provenance
<!-- @end:section_order -->

<!-- @pref:formatting version=2 -->
- PM uses emoji 🔴🟡🟢 for issue priority — keep this convention
- PM prefers bullet lists over tables for issues, tables for events
- PM always includes [^source] footnotes — never strip
<!-- @end:formatting -->

<!-- @pref:tone version=1 -->
- German for all content
- English only in code blocks and IDs
<!-- @end:tone -->
```

---

## 4. Anchor write rules (Patcher must obey)

1. **Never modify outside `<!-- @section: -->...<!-- @end: -->` markers.** Anything below `## PM Notes (human-owned)` heading also forbidden.
2. **Increment `version=N`** on every successful patch.
3. **Update frontmatter** `last_patched`, `patcher_commit`, derived counters (`open_issues_count`, `health_score`).
4. **Footnotes go in `provenance` anchor** — never inline new `[^X]` definitions elsewhere.
5. **Conflict policy:** if new content contradicts existing, write to `_pending_review.md`, log it, do not overwrite.
6. **Atomic writes:** write to tempfile → fsync → rename → git commit. Single commit per ingest event (squash all section patches).
7. **Read `schema/style.md` before write** — apply learned PM preferences.

---

## 5. Wikilink convention

- `[[EH-014]]` resolves to `wiki/LIE-001/HAUS-12/EH-014.md` (filename-based)
- `[[MIE-014]]` → `wiki/LIE-001/mieter/MIE-014.md`
- Obsidian auto-resolves filename-only wikilinks across vault. Graph view free.
- Provenance footnotes use `[^ID]` not wikilinks (different namespace — these point to `normalize/`, not wiki).

---

## 6. Health score (derived, in frontmatter)

Formula (per HAUS):

```
health = 1.0
       - 0.10 × open_issues_count
       - 0.20 × overdue_invoices_count
       - 0.05 × stale_facts_count          (last_patched on critical anchor > 90d)
       - 0.10 × pending_review_count
clamped to [0, 1]
```

Linter recomputes nightly. Dataview in `wiki/index.md` aggregates → live dashboard.
