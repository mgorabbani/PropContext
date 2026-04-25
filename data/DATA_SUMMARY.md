# Hackathon Data — Summary

Synthetic dataset for German **WEG (Wohnungseigentümergemeinschaft)** property management. Verwalter = `Huber & Partner Immobilienverwaltung GmbH`. Liegenschaft = `WEG Immanuelkirchstraße 26, 10405 Berlin` (3 buildings, 52 units, 35 owners, 26 tenants, 16 service providers). Time range: **2024-01 → 2026-01**.

---

## Top-level layout

```
hackathon/
├── stammdaten/      # master data (parties, units, building)
├── bank/            # full 2-year account statement
├── emails/          # ~6,500 .eml files, monthly subdirs
├── briefe/          # 135 outgoing letter PDFs, monthly subdirs
├── rechnungen/      # 194 invoice PDFs, monthly subdirs
└── incremental/     # day-01..day-10 delta packs (Jan 2026)
```

---

## 1. `stammdaten/` — master data (golden source)

| File | Rows | Content |
|---|---|---|
| `stammdaten.json` | — | unified blob: `liegenschaft`, `gebaeude` (3), `einheiten` (52), `eigentuemer` (35), `mieter` (26), `dienstleister` (16) |
| `dienstleister.csv` | 16 | service providers (Hausmeister, Aufzug, Versorger…) — IBAN, USt-ID, hourly rate |
| `eigentuemer.csv` | 35 | owners — selbstnutzer flag, SEV-mandat, beirat, mapping `einheit_ids` (EH-…) |
| `mieter.csv` | 26 | tenants — Kaltmiete, NK-Vorauszahlung, Kaution, IBAN, Mietbeginn/-ende |
| `einheiten.csv` | 52 | units — Haus/WE-Nr, qm, Zimmer, Miteigentumsanteil |

**Key IDs:** `LIE-001`, `HAUS-12/-13/-…`, `EH-001..EH-052`, `EIG-001..EIG-035`, `MIE-001..MIE-026`, `DL-001..DL-016`.

**Key bank accounts (in liegenschaft):**
- WEG-Konto: `DE02 1001 0010 0123 4567 89` (Postbank) — operating
- Rücklage: `DE12 1203 0000 0098 7654 32` (BayernLB) — reserves
- Verwalter: `DE89 3704 0044 0532 0130 00` (Commerzbank)

---

## 2. `bank/` — account statements (Jan 2024 – Dec 2025)

| File | Format | Rows |
|---|---|---|
| `bank_index.csv` | flat normalized index | 1,619 transactions |
| `kontoauszug_2024_2025.csv` | Sparkasse-style DTAUS export (semicolon, DD.MM.YYYY, comma decimals) | 1,619 |
| `kontoauszug_2024_2025.camt053.xml` | ISO 20022 CAMT.053 statement | same data |

**Three views of same data.** Opening balance 45.000,00 €, closing 933.582,62 € (2025-12-31).

**Categories (from `bank_index.csv`):** miete (624), hausgeld (806), dienstleister (155), versorger (8), sonstige (26). Direction: 1432 CREDIT / 187 DEBIT.

`bank_index` schema: `id,datum,typ,betrag,kategorie,gegen_name,verwendungszweck,referenz_id,error_types`. `referenz_id` ties to `EH-…` / `MIE-…` / `DL-…` / `INV-…`.

`error_types` column ⇒ dataset includes seeded errors/anomalies (challenge for matching/reconciliation).

---

## 3. `emails/` — inbox/outbox `.eml` files

- ~6,546 files across 25 monthly dirs `2024-01` .. `2026-01`
- Filename: `YYYYMMDD_HHMMSS_EMAIL-NNNNN.eml`
- Plain RFC 822 — From/To/Subject/Date headers + body, German + occasional EN
- Counterparties: tenants, owners, service providers, authorities
- Inbox is `info@huber-partner-verwaltung.de`

No dedicated index in root — incremental day folders carry an `emails_index.csv` with: `id,datetime,thread_id,direction,from_email,to_email,subject,category,sprache,error_types,filename,month_dir`. Categories like `eigentuemer/rechtlich`, `mieter/kaution`, `versorger/versorger`.

---

## 4. `briefe/` — outgoing letter PDFs

135 PDFs across `2024-04` .. `2025-12`. Filename: `YYYYMMDD_<typ>_LTR-NNNN.pdf`.

| Typ | Count | Meaning |
|---|---|---|
| etv_einladung | 70 | Eigentümerversammlung invitation |
| hausgeld | 35 | Hausgeld notice |
| bka | 13 | Betriebskostenabrechnung |
| mahnung | 10 | dunning |
| mieterhoehung | 3 | rent increase |
| protokoll | 2 | meeting minutes |
| kuendigung | 2 | termination |

---

## 5. `rechnungen/` — incoming invoice PDFs

194 PDFs across `2024-01` .. `2025-12`. Filename: `YYYYMMDD_DL-NNN_INV-NNNNN.pdf`. Dienstleister-ID ties back to `stammdaten/dienstleister.csv`.

---

## 6. `incremental/day-01..day-10/` — delta packs (Jan 2026)

10 daily sealed deltas simulating live ingest. Each day folder:

```
day-NN/
├── incremental_manifest.json   # day_index, content_date, seed, difficulty, counts, note
├── emails_index.csv            # ~3 incoming emails for the day
├── rechnungen_index.csv        # 1 invoice
├── bank/
│   └── kontoauszug_delta.csv   # 1 bank line (Sparkasse format)
├── emails/2026-01/             # actual .eml files
└── rechnungen/2026-01/         # actual PDF
```

Manifest: `schema_version=1`, `seed=42`, `difficulty=medium`, references parent `../stammdaten/stammdaten.json`. Note: *"Nur Delta-Dateien. Basis-Paket … liegt im uebergeordneten Ordner."* → must merge with root data.

Per-day volumes: ~3–4 emails, 1 invoice, 1 bank tx → designed for incremental matching/automation challenge.

---

## How datasets connect

```
stammdaten (IDs)  ──┐
                    ├─→ rechnungen (DL-id, INV-id)
emails (subjects, refs)
        └─→ thread_id, INV-, EH-, MIE- references in body
                    │
bank_index (referenz_id) ──→ MIE-/EH-/DL-/INV-/TX-
                    │
briefe (LTR-NNNN)  addressed to EIG-/MIE-/EH-
                    │
incremental days   ──→ append-only continuation into 2026-01
```

**Likely hackathon task:** build pipeline that ingests deltas, parses .eml + PDF, reconciles bank tx ↔ invoices ↔ tenants/owners ↔ stammdaten, surfaces anomalies (`error_types` column hints at seeded edge cases — wrong IBAN, missing reference, duplicates, etc.).

---

## Format gotchas

- German CSVs: `;` separator, `DD.MM.YYYY`, `1.088,85` decimal
- `bank_index.csv` uses `,` separator + `YYYY-MM-DD` + `.` decimal — different convention from CAMT/DTAUS pair
- IBAN sometimes spaced (`DE02 1001…`), sometimes not (`DE02100100100123456789`) — normalize before joining
- Encoding mostly UTF-8; .eml uses quoted-printable
- `error_types` non-empty rows = intentionally dirty data
