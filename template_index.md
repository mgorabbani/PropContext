---
# ════════════════════════════════════════════════════════════════════════════
#  BaC — Building-as-Code · Hermes-Wiki Engine
#  FILE:    wiki/{{LIE_ID}}/{{HAUS_ID}}/index.md
#  ROLE:    Agent-facing canonical building context. Human-auditable.
#  SCHEMA:  Version 1 · Template Version 1.1.0
#
#  PRIMARY CONSUMER:   AI agent (dense, chunk-level RAG retrieval)
#  SECONDARY CONSUMER: Human PM (audit, annotations in PM Notes only)
#
#  COMPLETENESS CONTRACT:
#    This file is the authoritative reconstruction surface.
#    Every historical fact is either inline OR accessible via:
#      (a) archive_index → _archive/{{HAUS_ID}}/
#      (b) provenance footnotes → normalize/ source files
#    No fact may be discarded without Archive-First Protocol (§archive_index).
# ════════════════════════════════════════════════════════════════════════════

# ── Core identity (WIKI_SCHEMA §2 — required fields) ──────────────────────
id:               "{{HAUS_ID}}"           # e.g. HAUS-12
type:             gebaeude
parent:           "{{LIE_ID}}"            # e.g. LIE-001
children:         []                      # Patcher populates: [EH-001, EH-002, ...]
created_at:       "{{ISO_TIMESTAMP}}"     # e.g. 2026-04-25T10:00:00Z
last_patched:     "{{ISO_TIMESTAMP}}"
patcher_commit:   "{{GIT_HASH}}"
schema_version:   1
template_version: "1.1.0"                # Bump on structural template changes

# ── Type-specific fields: gebaeude ─────────────────────────────────────────
address:     "{{STRASSE}} {{NR}}, {{HAUS_TYP}}, {{PLZ}} {{STADT}}"
units_count: 0
qm_total:    0.0
baujahr:     0
# Energieausweis details live in legal_documents; class here enables Dataview filtering
energieausweis_klasse:  "{{A+|A|B|C|D|E|F|G|H}}"
energieausweis_expiry:  "{{YYYY-MM-DD}}"
denkmalschutz:          false

# ── Derived health metrics (Linter recomputes nightly via cron) ────────────
# Formula: health = 1.0 - 0.10×open_issues_count - 0.20×overdue_invoices_count
#                       - 0.05×stale_facts_count  - 0.10×pending_review_count
#          clamped to [0.0, 1.0]
health_score:            0.00
open_issues_count:       0
overdue_invoices_count:  0
stale_facts_count:       0    # sections where last_patched > FRESHNESS_CEILING
pending_review_count:    0

# ── RAG token budget (chunk-level retrieval — each @section is one chunk) ──
# Linter alerts in log.md if any section exceeds its ceiling.
# Patcher must split sections that consistently exceed ceiling by >20%.
retrieval_profile:
  tier0_ceiling_tokens: 200    # per section; 3 sections; total Tier0 target ≤ 600
  tier1_ceiling_tokens: 500    # per section; 6 sections; total Tier1 target ≤ 2000
  tier2_ceiling_tokens: 500    # per section; 7 sections; total Tier2 target ≤ 2500

# ── Hermes loop state ──────────────────────────────────────────────────────
# TRIGGER MODEL (hybrid — full spec in hermes_meta section):
#   EVENT:    ingest tool_calls ≥ skill_extraction_threshold → skill extraction
#   PERIODIC: nudge_counter mod 15 == 0 → structure optimization eval
#   CRON:     nightly → health, freshness, contradiction detection
hermes_nudge_counter:         0
skill_extraction_threshold:   5      # tool calls per task; Hermes default
last_skill_extracted:         null   # ISO timestamp
last_structure_eval:          null   # ISO timestamp
feedback_log:                 "_hermes_feedback.jsonl"  # relative to this file

# ── Archive pointer (Archive-First Protocol) ───────────────────────────────
archive_ref: "_archive/{{HAUS_ID}}/"

tags: [building, weg]
---

# {{HAUS_ID}} — {{HAUS_BEZEICHNUNG}}

<!-- ══════════════════════════════════════════════════════════════════════
     AGENT READING CONTRACT — READ BEFORE PARSING
     ─────────────────────────────────────────────────────────────────────
     RETRIEVAL TOPOLOGY:
       Each <!-- @section:KEY --> block is an INDEPENDENT RAG chunk.
       Sections are ordered by retrieval priority (Tier 0 first).
       Section headers + opening lines carry highest retrieval weight:
       make them semantically specific, not generic.

     TIER 0 (sections 1–3): Emergency / access / critical issues.
               Always retrieve for ANY query involving this building.
     TIER 1 (sections 4–9): Operational. Covers ~80% of PM agent tasks.
     TIER 2 (sections 10–16): Deep / historical. Reference queries.
     META   (sections 17–18): Agent loop state. Not for human action.

     WRITE RULES (Patcher):
       - Never modify content outside @section...@end markers.
       - Never write below "## PM Notes" heading.
       - Increment version=N on every successful patch.
       - Resolve conflicts → _pending_review.md (never auto-overwrite).
       - Archive-First: content removal requires archive_index entry first.
       - See WIKI_SCHEMA §4 for complete Patcher rules.

     VOCABULARY:
       Risk levels:   niedrig | mittel | hoch | kritisch
       Unit status:   vermietet | leer | leerstehend | Eigenbedarf | Renovierung
       Issue prio:    🔴 Sofort (≤48h) | 🟡 Dringend (≤14d) | 🟢 Geplant
       Payment:       pünktlich | verspätet_<N>d | ausstehend | Widerspruch
     ══════════════════════════════════════════════════════════════════════ -->


<!-- ══════════════════════════════════════════════════════════════════════
     TIER 0 — CRITICAL
     Staleness ceiling: 30 days for all Tier 0 sections.
     Linter flags as stale_fact if last_patched > 30d on any Tier 0 section.
     Patcher must validate Tier 0 content on EVERY ingest event, even if no
     patch is needed — confirm with a no-op version bump and log.md entry.
     ══════════════════════════════════════════════════════════════════════ -->

<!-- @section:emergency_dispatch version=0
     FRESHNESS: 30d | TIER: 0 | TOKEN_CEILING: 200
     PURPOSE: Immediate action lookup for any emergency scenario.
     AGENT: Read this section first for any incident or safety query.
     PATCHER: Verify all phone numbers against DL-*.md on each update. -->
## Notfalldispatch & Sofortmaßnahmen

| Szenario | Sofortmaßnahme | Kontakt | Verfügbarkeit |
|---|---|---|---|
| Gasgeruch / Gasleck | Gas-Haupthahn schließen ({{STANDORT_GASHAHN}}), Gebäude räumen | Gasnotdienst Berlin: **0800 222 2222** | 24/7 |
| Wasserrohrbruch | Wasserhauptventil schließen ({{STANDORT_WASSERVENTIL}}) | Hausmeister [[{{DL_HAUSMEISTER}}]]: {{TEL}} | Werktags |
| Heizungsausfall | → procedural_memory §heating-emergency | Notdienst [[{{DL_HEIZUNG}}]]: {{TEL}} | 24/7 |
| Brand | 112 sofort | Verwalter: {{VERWALTER_TEL}} | — |
| Aufzug: Einschluss | Notruftaste (Pflicht §41 BauO Bln) | Aufzugnotdienst [[{{DL_AUFZUG}}]]: {{TEL}} | 24/7 |
| Einbruch / Vandalismus | 110 | Hausmeister | — |

**Verwalter:** Huber & Partner — {{VERWALTER_TEL}} — Büro: {{ZEITEN}}
<!-- @end:emergency_dispatch -->


<!-- @section:active_critical_issues version=0
     FRESHNESS: 7d | TIER: 0 | TOKEN_CEILING: 200
     PURPOSE: 🔴 Sofort-Punkte only — requires action within 48h.
     PRUNE RULE: When severity drops to 🟡/🟢 → move row to open_issues section.
                 When resolved → Archive-First Protocol, then remove row.
     EMPTY STATE: If no critical issues, write exactly the empty-state line below. -->
## Kritische Punkte — Sofortbedarf (🔴)

<!-- EMPTY STATE (use when no critical issues):
     > _Keine kritischen Punkte. Geprüft: {{YYYY-MM-DD}}_              -->

| EH | Beschreibung | Verantwortlich | Frist | Stand | Quelle |
|---|---|---|---|---|---|
| [[EH-000]] | [Kurzbeschreibung des Problems] | [[DL-000]] | YYYY-MM-DD | in_progress | [^SRC] |

<!-- @end:active_critical_issues -->


<!-- @section:access_and_security version=0
     FRESHNESS: 30d | TIER: 0 | TOKEN_CEILING: 150
     PURPOSE: All physical access credentials for contractor dispatch.
     SECURITY: Excluded from any external-facing export or API response.
     CHANGE RULE: Any credential change → immediate version bump + log.md entry.
     PATCHER: Cross-check codes against EMAIL/BRIEF sources before writing. -->
## Zugang & Sicherheit

- **Keybox Haupteingang:** `{{CODE}}` — geändert: {{YYYY-MM-DD}} [^{{SRC}}]
- **Heizungsraum-Schlüssel:** bei [[{{DL_ID}}]] — **nicht** beim Hausmeister [^{{SRC}}]
- **Keller / Technikraum:** {{Schlüssel bei DL-ID | Keybox Code}}
- **Alarmanlage PIN:** `{{PIN | n/a}}`
- **Dachboden:** {{Zugang}}

<!-- @end:access_and_security -->


<!-- ══════════════════════════════════════════════════════════════════════
     TIER 1 — DYNAMIC
     These sections cover ~80% of PM agent operational tasks.
     Staleness ceilings vary; annotated per section.
     ══════════════════════════════════════════════════════════════════════ -->

<!-- @section:open_issues version=0
     FRESHNESS: 14d | TIER: 1 | TOKEN_CEILING: 500
     PURPOSE: Full rolling issue register — all severities and lifecycle stages.
     LIFECYCLE: offen → zugewiesen → in_progress → gelöst → archiviert
     PRUNE RULE: Status=gelöst AND older than 60d → Archive-First, then remove.
     AGENT: Check here before any outbound action (letter, call, dispatch). -->
## Offene Punkte

| Prio | Beschreibung | EH | Verantwortlich | Frist | Status | Quelle |
|---|---|---|---|---|---|---|
| 🔴 | [Problem] | [[EH-000]] | [[DL-000]] | YYYY-MM-DD | in_progress | [^SRC] |
| 🟡 | [Problem] | [[EH-000]] | [[EIG-000]] | YYYY-MM-DD | zugewiesen | [^SRC] |
| 🟢 | [Problem] | — | intern | YYYY-MM-DD | offen | [^SRC] |

<!-- @end:open_issues -->


<!-- @section:tenancy_snapshot version=0
     FRESHNESS: 30d | TIER: 1 | TOKEN_CEILING: 500
     PURPOSE: Current-state EH→Mieter→Zahlungsstatus map.
     SCOPE: Current state snapshot ONLY. For historical reconstruction:
            - Full payment history → individual MIE-*.md files
            - Past tenants / past rent rates → archive_index
            - All data reconstructable from provenance footnotes
     SPLIT RULE: If >15 units in this section → split by floor (EG, 1.OG, ...).
     PAYMENT VALUES: pünktlich | verspätet_<N>d | ausstehend | Widerspruch
     AGENT: "Zahlt Mieter X pünktlich?" / "Ist EH-007 leer?" → answer here. -->
## Mieterübersicht (Snapshot — {{YYYY-MM-DD}})

| EH | Lage | Mieter | Kaltmiete | Letzte Zahlung | Status | Mieterhöhung / Widerspruch | Mietbeginn |
|---|---|---|---|---|---|---|---|
| [[EH-001]] | EG li | [[MIE-001]] Name | 850,00 € | YYYY-MM-DD | pünktlich | — | YYYY-MM-DD |
| [[EH-002]] | EG re | leer | — | — | — | — | — |
| [[EH-003]] | 1.OG li | [[MIE-003]] Name | 920,00 € | YYYY-MM-DD | Widerspruch | Erhöhung 2026-04, Frist 2026-05-15 [^SRC] | YYYY-MM-DD |

<!-- @end:tenancy_snapshot -->


<!-- @section:contractor_roster version=0
     FRESHNESS: 90d | TIER: 1 | TOKEN_CEILING: 400
     PURPOSE: Active contractor directory with dispatch protocol and SLA.
     DISPATCH ORDER: See procedural_memory for category-specific sequences.
     AGENT: "Wer repariert die Heizung?" → DL-ID + Telefon + SLA hier. -->
## Dienstleister (Aktiv)

| Kategorie | Firma | ID | Telefon | SLA Notfall | Vertrag bis | 24/7? |
|---|---|---|---|---|---|---|
| Hausmeister | {{FIRMA}} | [[DL-003]] | {{TEL}} | 1 Werktag | {{DATE}} | Nein |
| Heizung | {{FIRMA}} | [[DL-007]] | {{TEL}} | 2–4h | {{DATE}} | Ja |
| Reinigung | {{FIRMA}} | [[DL-005]] | {{TEL}} | — | {{DATE}} | Nein |
| Versicherung | {{FIRMA}} | [[DL-011]] | {{TEL}} | — | {{DATE}} | Nein |
| Aufzug | n/a | — | — | — | — | — |

_Leistungsbewertung & Rechnungshistorie: jeweilige DL-*.md Datei_
<!-- @end:contractor_roster -->


<!-- @section:procedural_memory version=0
     FRESHNESS: 180d | TIER: 1 | TOKEN_CEILING: 500
     PURPOSE: Extracted procedural skills from successful task trajectories.
     SOURCE: Auto-written by Patcher when task tool_calls ≥ skill_extraction_threshold.
     CONFIDENCE: successful_uses / total_uses. Review if < 0.50 after ≥3 uses.
     PRUNE RULE: confidence < 0.40 after ≥5 uses → flag for PM review, NOT auto-delete.
     HUMAN EDIT: PMs may annotate steps (prefix annotation with ※). Patcher preserves.
     AGENT: Retrieve relevant @skill block before executing any multi-step task. -->
## Prozedurales Gedächtnis (Gelernte Abläufe)

<!-- SKILL BLOCK TEMPLATE — copy, fill in, remove this comment block:

<!-- @skill:{{SKILL_ID}} version=0 confidence=0.00 uses=0 extracted={{YYYY-MM-DD}} -->
**Wenn:** {{TRIGGER_CONDITION}} — Geltungsbereich: {{HAUS_ID | alle HAUS}}
**Schritte:**
1. {{SCHRITT_1}} — Kontakt: [[{{DL_ID}}]] ({{TEL}})
2. {{SCHRITT_2}}
3. {{SCHRITT_3}}
**Fallback (kein Ergebnis nach {{N}} min):** {{FALLBACK}} — [[{{DL_BACKUP_ID}}]]
**Doku-Pflicht:** {{WHAT_TO_DOCUMENT_AND_WHERE}}
**Quellen:** {{TRAJECTORY_IDS}} | **Confidence:** {{0.00}} | **Anwendungen:** {{N}}
<!-- @end:skill:{{SKILL_ID}} -->

-->

<!-- @end:procedural_memory -->


<!-- @section:recent_events version=0
     FRESHNESS: daily | TIER: 1 | TOKEN_CEILING: 500
     PURPOSE: Rolling 60-day event log for operational pattern recognition.
     COMPLETENESS: Events older than 60d are ARCHIVED (Archive-First), never deleted.
                   Full append-only canonical log: LIE-001/log.md (never pruned).
                   Historical reconstruction uses: archive_index + log.md + provenance.
     SORT: Descending by date (newest first).
     TYPES: email | invoice | bank | letter | event | inspection | legal -->
## Ereignisprotokoll (Letzte 60 Tage)

| Datum | Typ | Zusammenfassung | Entitäten | Quelle |
|---|---|---|---|---|
| YYYY-MM-DD | email | [Kurzbeschreibung] | [[EH-000]], [[DL-000]] | [^SRC] |
| YYYY-MM-DD | invoice | [Firma, Betrag, Status] | [[DL-000]] | [^INV] |
| YYYY-MM-DD | bank | [Transaktion, Betrag, Richtung] | [[MIE-000]] | [^TX] |
| YYYY-MM-DD | letter | [Brieftyp, Empfänger] | [[EIG-000]] | [^LTR] |

<!-- @end:recent_events -->


<!-- @section:weg_compliance version=0
     FRESHNESS: 90d | TIER: 1 | TOKEN_CEILING: 400
     PURPOSE: WEG-Gesetz compliance status — statutory obligations.
     RÜCKLAGE FORMULA (§19 WEGesetz — target for adequacy check in financial_snapshot):
       Target = max(12 €/qm/Jahr, Gebäudealter_Jahre × 0.9 €/qm/Jahr) × qm_total
       For {{HAUS_ID}}: {{N}} Jahre alt, {{QM}} m² → Target = {{BETRAG}} €/Jahr
     AGENT: "Wann ist die nächste ETV?" / "Welche Beschlüsse sind noch offen?" -->
## WEG-Compliance & Verwaltung

**Eigentümerversammlung (ETV)**
- Letzte ETV: {{YYYY-MM-DD}} — Protokoll: [^{{LTR_ID}}]
- Nächste ETV (Pflicht bis 31.12.{{YYYY}}): {{YYYY-MM-DD}} — Einladungsfrist: 21 Tage
- Beschlussfähigkeit: erfordert Eigentümer mit > 50% MEA-Anteil (§ 25 WEGesetz)
- Letztes Quorum: {{N}} Eigentümer / {{MEA_PROZENT}}% MEA

**Verwaltervertrag**
- Verwalter: Huber & Partner Immobilienverwaltung GmbH
- Laufzeit: {{START}} – {{END}} (Verlängerungsklausel: {{DETAILS}}) [^{{SRC}}]
- Kündigung bis: {{YYYY-MM-DD}} ({{N}} Monate Frist)

**Offene Beschlüsse (ETV-Beschlüsse, nicht umgesetzt)**
- ETV {{YYYY}}, TOP {{N}}: {{BESCHREIBUNG}} — Umsetzungsfrist: {{YYYY-MM-DD}} [^{{LTR_ID}}]
- _Keine offenen Beschlüsse_ (wenn zutreffend)

**Hausgeld-Rückstände**
- Rückstände gesamt: {{N}} Eigentümer, {{BETRAG}} € offen (Details: EIG-*.md)
<!-- @end:weg_compliance -->


<!-- ══════════════════════════════════════════════════════════════════════
     TIER 2 — STATIC
     Staleness ceilings: 90–365 days (annotated per section).
     Retrieved for deep queries, historical reconstruction, compliance audits.
     ══════════════════════════════════════════════════════════════════════ -->

<!-- @section:core_metadata version=0
     FRESHNESS: 365d | TIER: 2 | TOKEN_CEILING: 300
     PURPOSE: Near-immutable building identity facts.
     NOTE: Energieausweis details in legal_documents; class mirrored in frontmatter. -->
## Stammdaten Gebäude

- **Adresse:** {{STRASSE}} {{NR}}, {{HAUS_TYP}}, {{PLZ}} {{STADT}}
- **Gebäudetyp:** {{Vorderhaus | Seitenflügel | Hinterhaus | Einzelgebäude}}
- **Baujahr:** {{YYYY}}
- **Einheiten:** {{N}} ({{EH-FIRST}} – {{EH-LAST}})
- **Gesamtfläche:** {{QM_TOTAL}} m²
- **Miteigentumsanteile gesamt:** {{MEA_SUM}} / {{MEA_GESAMT}} (Teilungserklärung: [^{{SRC}}])
- **Energieausweis:** Klasse {{X}}, gültig bis {{YYYY-MM-DD}} → [^{{SRC}}]
- **Denkmalschutz:** {{ja (Aktenzeichen: {{AZ}}) | nein}}
- **Koordinaten:** {{LAT}}, {{LON}}
<!-- @end:core_metadata -->


<!-- @section:physical_infrastructure version=0
     FRESHNESS: 90d | TIER: 2 | TOKEN_CEILING: 500
     PURPOSE: MEP lifecycle tracking — authoritative for maintenance planning.
     RISK VOCAB: niedrig | mittel | hoch | kritisch: <description>
     AGENT: "Wann ist die nächste Boilerwartung?" / "Zustand Steigleitungen?" -->
## Technische Infrastruktur (MEP-Lifecycle)

**Heizungsanlage**
- System: {{HERSTELLER}} {{MODELL}}, {{Gas | Öl | Fernwärme | Wärmepumpe}}
- Installiert: {{YYYY}} [^{{INV_ID}}] | Wartungsvertrag: [[{{DL_ID}}]], {{BETRAG}} €/Jahr
- Letzte Wartung: {{YYYY-MM-DD}} [^{{INV_ID}}] | Nächste fällig: {{YYYY-MM-DD}}
- Risiko: {{RISK_LEVEL}}: {{RISK_DESCRIPTION}}

**Warmwasser / Boiler**
- Letzte Wartung: {{YYYY-MM-DD}} [^{{INV_ID}}] | Nächste fällig: {{YYYY-MM-DD}}
- Risiko: {{RISK_LEVEL}}: {{RISK_DESCRIPTION}}

**Steigleitungen (Wasser)**
- Material: {{Kupfer | Stahl | Kunststoff}} | Geschätztes Alter: {{N}} Jahre
- Letzter Befund: {{YYYY-MM-DD}} [^{{SRC}}] — Ergebnis: {{OK | Risiko | Sanierung empfohlen}}
- Risiko: {{RISK_LEVEL}}: {{RISK_DESCRIPTION}}

**Dach**
- Letzte Sanierung: {{YYYY}} [^{{LTR_ID}}] | Garantie bis: {{YYYY-MM-DD}}
- Nächste Inspektion: {{YYYY-MM-DD}} | Zustand: {{gut | mittel | Sanierungsbedarf}}

**Aufzug**
- Vorhanden: {{ja | nein}}
- TÜV-Abnahme: {{YYYY-MM-DD}} | Nächste Pflichtprüfung: {{YYYY-MM-DD}} [^{{SRC}}]

**Elektro / Zählerschrank**
- Letzter E-Check (§5 DGUV V3): {{YYYY-MM-DD}} | Nächster: {{YYYY-MM-DD}}
- Zustand: {{Beschreibung}}

**Rauchwarnmelder (§45 Abs. 6 BauO Bln — Pflicht)**
- Installiert: {{YYYY-MM-DD}} | Verantwortlich: {{WEG | Mieter (vertraglich)}}
- Letzter Nachweis-Check: {{YYYY-MM-DD}} | Nächster: {{YYYY-MM-DD}}
- Einheiten ohne Nachweis: {{N}} — Details: open_issues

**Keller / Allgemeinbereiche**
- {{BESCHREIBUNG_ZUSTAND}}
<!-- @end:physical_infrastructure -->


<!-- @section:financial_snapshot version=0
     FRESHNESS: 90d | TIER: 2 | TOKEN_CEILING: 400
     PURPOSE: WEG financial position — data AND adequacy assessment co-located.
     NOTE: Snapshot only. Authoritative: bank_index.csv + Jahresabrechnung.
     RÜCKLAGE ADEQUACY: Formula from weg_compliance; data + verdict here together.
     AGENT: "Können wir die Treppenhaus-Renovierung finanzieren?" → answer here. -->
## Finanzübersicht (Snapshot — {{YYYY-MM-DD}})

**Konten**
- WEG-Betriebskonto: {{BETRAG}} € [^{{TX_ID}}]
- Instandhaltungsrücklage: {{BETRAG}} € [^{{TX_ID}}]

**Instandhaltungsrücklage — Adequacy-Check**
- Aktueller Bestand: {{BETRAG}} €
- Zielwert (Altbau-Formel, {{N}} Jahre, {{QM}} m²): {{ZIELWERT}} €
- **Status:** ✅ ausreichend | ⚠️ knapp ({{PROZENT}}% des Ziels) | 🔴 unzureichend
- Beitragssatz: {{BETRAG}} €/MEA/Monat — Wirtschaftsplan {{YYYY}} [^{{LTR_ID}}]

**Hausgeld**
- Wirtschaftsplan {{YYYY}}, genehmigt {{YYYY-MM-DD}} [^{{LTR_ID}}]
- Beitrag pro MEA: {{BETRAG}} €/Monat

**Aktive Sonderumlagen**
- {{BESCHREIBUNG}}: {{BETRAG}} € gesamt, fällig {{YYYY-MM-DD}} [^{{LTR_ID}}]
- _Keine aktiven Sonderumlagen_ (wenn zutreffend)

**Jahresabrechnung**
- Abrechnungsjahr: {{YYYY}} | Versandt: {{YYYY-MM-DD}} [^{{LTR_ID}}]
- Offene Rückfragen: {{N}} Eigentümer
<!-- @end:financial_snapshot -->


<!-- @section:unit_register version=0
     FRESHNESS: 90d | TIER: 2 | TOKEN_CEILING: 500
     PURPOSE: One-line quick reference per Einheit in this building.
     SPLIT RULE: If section exceeds 500 tokens → split by floor (EG, 1.OG, 2.OG...).
     STATUS VALUES: vermietet | leer | leerstehend | Eigenbedarf | Renovierung
     MEA-SUMME must match Teilungserklärung; flag any discrepancy in open_issues.
     AGENT: "MEA von EH-014?" / "Welche Einheiten stehen leer?" -->
## Einheitenregister

| EH | Lage | m² | Zi | MEA | Eigentümer | Mieter | Status |
|---|---|---|---|---|---|---|---|
| [[EH-001]] | EG li | 00.0 | 0.0 | 00.0 | [[EIG-000]] | [[MIE-000]] | vermietet |
| [[EH-002]] | EG re | 00.0 | 0.0 | 00.0 | [[EIG-000]] | — | leer |
| [[EH-003]] | 1.OG li | 00.0 | 0.0 | 00.0 | [[EIG-000]] | [[MIE-000]] | Eigenbedarf |

_MEA-Summe: {{SUMME}} / Soll (Teilungserklärung): {{SOLL}} — Delta: {{DELTA}}_
<!-- @end:unit_register -->


<!-- @section:legal_documents version=0
     FRESHNESS: 365d | TIER: 2 | TOKEN_CEILING: 300
     PURPOSE: Authoritative index of key legal documents with validity and location.
     AGENT: "Wo liegt der Verwaltervertrag?" / "Läuft die Gebäudeversicherung noch?" -->
## Rechtsdokumente

| Dokument | Ausgestellt | Gültig bis | Ablage | Quelle |
|---|---|---|---|---|
| Teilungserklärung | {{YYYY-MM-DD}} | unbefristet | `stammdaten/teilungserklaerung.pdf` | [^{{SRC}}] |
| Gemeinschaftsordnung | {{YYYY-MM-DD}} | unbefristet | `stammdaten/gemeinschaftsordnung.pdf` | [^{{SRC}}] |
| Verwaltervertrag | {{YYYY-MM-DD}} | {{YYYY-MM-DD}} | `stammdaten/verwaltervertrag.pdf` | [^{{SRC}}] |
| Hausordnung | {{YYYY-MM-DD}} | unbefristet | `stammdaten/hausordnung.pdf` | [^{{SRC}}] |
| Gebäudeversicherung | {{YYYY-MM-DD}} | {{YYYY-MM-DD}} | `stammdaten/versicherung_{{YYYY}}.pdf` | [^{{SRC}}] |
| Energieausweis | {{YYYY-MM-DD}} | {{YYYY-MM-DD}} | `stammdaten/energieausweis.pdf` | [^{{SRC}}] |
| Beschlussbuch | lfd. | — | `wiki/{{LIE_ID}}/beschlussbuch.md` | — |
| ETV-Protokoll {{YYYY}} | {{YYYY-MM-DD}} | — | [^{{LTR_ID}}] | [^{{SRC}}] |
<!-- @end:legal_documents -->


<!-- @section:archive_index version=0
     FRESHNESS: N/A — append-only | TIER: 2 | TOKEN_CEILING: 300
     PURPOSE: Index of all archived content. Enforces the Archive-First Protocol.

     ── ARCHIVE-FIRST PROTOCOL (mandatory before ANY content removal) ────────
     Before Patcher removes content from any section:
       STEP 1. Write full section snapshot to:
               _archive/{{HAUS_ID}}/YYYY-MM-DD_{{section_key}}_v{{N}}.md
               File MUST include: section content + all referenced provenance footnotes.
       STEP 2. Create git tag: archive/{{HAUS_ID}}/{{section_key}}/v{{N}}
       STEP 3. Append row to this table.
       STEP 4. Append entry to LIE-001/log.md with reason + patcher_commit.
       STEP 5. Only then modify or remove the original section content.

     This 5-step protocol ensures any historical fact is reconstructable from
     building.md alone, without accessing raw source files.
     ──────────────────────────────────────────────────────────────────────── -->
## Archivindex

| Datum | Abschnitt | Grund | Archivpfad | Git-Tag |
|---|---|---|---|---|
| YYYY-MM-DD | {{section_key}} | {{Grund}} | `_archive/{{HAUS_ID}}/YYYY-MM-DD_{{section_key}}_vN.md` | `archive/{{HAUS_ID}}/{{section_key}}/vN` |

<!-- @end:archive_index -->


<!-- @section:provenance version=0
     FRESHNESS: N/A — append-only | TIER: 2 | TOKEN_CEILING: 500
     PURPOSE: Source citations for ALL facts in this document.
     RULES:
       - Every [^ID] reference used above must be defined here.
       - Patcher adds footnotes ONLY in this section (never inline elsewhere).
       - Format: [^ID]: `normalize/TYPE/YYYY-MM/ID.md` → `raw/SOURCE/PATH`
       - Bank transactions: [^TX-N]: `bank_index.csv:{{ROW_ID}}`
       - Pending normalization: note as "pending normalization: {{raw_path}}" -->
## Quellenverzeichnis

[^EMAIL-00000]: `normalize/eml/YYYY-MM/EMAIL-00000.md` → `raw/emails/YYYY-MM-DD/....eml`
[^INV-00000]: `normalize/pdf/YYYY-MM/INV-00000.md` → `raw/rechnungen/YYYY-MM/....pdf`
[^LTR-0000]: `normalize/pdf/YYYY-MM/LTR-0000.md` → `raw/briefe/YYYY-MM/....pdf`
[^TX-0000]: `bank_index.csv:{{ROW_ID}}`
<!-- @end:provenance -->


<!-- ══════════════════════════════════════════════════════════════════════
     META — HERMES LOOP CONTROL
     Machine-managed. Human: read-only for audit purposes.
     Patcher owns these sections; PM should not edit directly.
     ══════════════════════════════════════════════════════════════════════ -->

<!-- @section:hermes_meta version=0
     FRESHNESS: Per-ingest | TIER: META | TOKEN_CEILING: 400
     PURPOSE: Hermes loop state and complete trigger specification for Patcher.

     ── TRIGGER ARCHITECTURE (hybrid — source: Hermes Agent v0.7+) ──────────

     [1] EVENT TRIGGER (primary — fires after every ingest task):
         Condition: ingest_task.tool_call_count >= skill_extraction_threshold (default: 5)
         Action:
           a. Run LLM skill extraction over task trajectory
           b. Write/update @skill block in procedural_memory section
           c. Increment hermes_nudge_counter in frontmatter
           d. Append JSONL entry to _hermes_feedback.jsonl:
              {
                "ts":                 "<ISO_TIMESTAMP>",
                "ingest_id":          "<EMAIL-ID|INV-ID|...>",
                "tool_calls":         <N>,
                "sections_read":      ["section_key", ...],
                "sections_patched":   ["section_key", ...],
                "retrieval_success":  <true|false>,
                "missing_context":    "<description|null>",
                "correction_applied": <true|false>,
                "skill_extracted":    <true|false>,
                "skill_id":           "<skill_id|null>"
              }

     [2] PERIODIC NUDGE (secondary — fires every 15 ingest events):
         Condition: hermes_nudge_counter mod 15 == 0
         Action:
           a. Read last 15 entries from _hermes_feedback.jsonl
           b. LLM evaluation prompt: "Which sections show retrieval_success=false
              consistently? Which missing_context patterns recur across tasks?"
           c. If optimization identified → write proposal to _pending_review.md
           d. PM approves → Patcher propagates to template_index.md + all HAUS files
           e. Archive-First Protocol applies to any content removal
           f. Update last_structure_eval in frontmatter

     [3] NIGHTLY CRON (maintenance — scheduled, fires regardless of ingest):
         Actions:
           a. Recompute health_score (formula in frontmatter comment)
           b. Flag sections where last_patched > FRESHNESS_CEILING → stale_facts_count
           c. Cross-check anchor facts for internal contradictions → _pending_review.md
           d. Update pending_review_count in frontmatter
           e. git commit -m "cron: health+freshness audit {{DATE}}"

     RATIONALE FOR HYBRID MODEL:
       Pure nightly cron misses the causal link between a specific task
       trajectory and the skill it should generate. Pure event trigger
       misses structural drift that only becomes visible across many tasks.
       The hybrid model (Hermes v0.7+ architecture) captures both signals.
       JSONL format chosen over Markdown: machine-queryable, SQLite-importable,
       and compatible with Hermes Agent's FTS5 session search architecture.
     ──────────────────────────────────────────────────────────────────────── -->

**Loop-Status**
- Nudge-Counter: `{{N}}` — nächste Struktur-Eval bei Ingest Nr. `{{N - (N mod 15) + 15}}`
- Letzte Skill-Extraktion: `{{YYYY-MM-DD HH:MM:SS}}` — Skill-ID: `{{SKILL_ID}}`
- Letzte Struktur-Eval: `{{YYYY-MM-DD}}`
- Feedback-Log: `{{N}}` Einträge in `_hermes_feedback.jsonl`
- Ausstehende Optimierungen: `{{N}}` Vorschläge in `_pending_review.md`
<!-- @end:hermes_meta -->


<!-- @section:schema_evolution version=0
     FRESHNESS: Per template version bump | TIER: META | TOKEN_CEILING: 200
     PURPOSE: Structural change history. Karpathy format for grep compatibility.
     grep "^\#\# \[" schema_evolution → machine-parseable version list. -->
## Template-Versionshistorie

## [2026-04-25 00:00:00] template_version=1.1.0
- Initiale Version — BerlinHackBuena · BaC Hermes-Wiki Engine
- Sections: 3×Tier0, 6×Tier1, 7×Tier2, 2×Meta = 18 Abschnitte gesamt
- Trigger-Modell: Hybrid (Event + Periodic Nudge + Nightly Cron)
- Archive-First Protocol: aktiv
- Rauchmelderpflicht §45 BauO Bln: integriert
- Rücklage-Adequacy-Formel §19 WEGesetz: in weg_compliance + financial_snapshot

<!-- @end:schema_evolution -->


---

## PM Notes (menschlich kontrolliert — Patcher schreibt hier NIEMALS)

<!-- Freier Bereich ausschließlich für manuelle Hausverwaltungsnotizen.
     Alles unterhalb dieser Überschrift: menschlich kontrolliert.
     Agenten LESEN diesen Bereich, aber modifizieren ihn NICHT.
     Wikilinks ([[ID]]) und Quellenverweise ([^ID]) funktionieren hier. -->
