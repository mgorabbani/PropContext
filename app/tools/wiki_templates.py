from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def _frontmatter(name: str, description: str) -> str:
    return f"---\nname: {name}\ndescription: {description}\n---\n\n"


def _human_notes_footer() -> str:
    return "\n# Human Notes\n"


def _section(heading: str, body: str = "") -> str:
    body = body.rstrip()
    if body:
        return f"## {heading}\n\n{body}\n\n"
    return f"## {heading}\n\n"


def _agent_managed_comment(format_hint: str) -> str:
    return f"<!-- agent-managed: {format_hint} -->\n"


def _bullet(text: str) -> str:
    return f"- {text}\n"


def _einheiten_for_haus(haus_id: str, einheiten: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [e for e in einheiten if e.get("haus_id") == haus_id]


def _mieter_for_einheit(einheit_id: str, mieter: list[dict[str, Any]]) -> dict[str, Any] | None:
    for m in mieter:
        if m.get("einheit_id") == einheit_id and m.get("mietende") is None:
            return m
    return None


def _eigentuemer_for_einheit(
    einheit_id: str, eigentuemer: list[dict[str, Any]]
) -> dict[str, Any] | None:
    for e in eigentuemer:
        if einheit_id in (e.get("einheit_ids") or []):
            return e
    return None


def _haus_for_einheit(einheit_id: str, einheiten: list[dict[str, Any]]) -> str | None:
    for e in einheiten:
        if e.get("id") == einheit_id:
            return e.get("haus_id")
    return None


def render_lie_index(stammdaten: dict[str, Any]) -> str:
    lie = stammdaten["liegenschaft"]
    gebaeude = stammdaten.get("gebaeude", [])
    einheiten = stammdaten.get("einheiten", [])
    eigentuemer = stammdaten.get("eigentuemer", [])
    mieter = stammdaten.get("mieter", [])
    dienstleister = stammdaten.get("dienstleister", [])
    lie_id = lie["id"]
    name = f"property-{lie_id.lower()}"

    haus_refs = ", ".join(g["id"] for g in gebaeude) or "none"
    sanierung = lie.get("sanierung")
    sanierung_part = f", saniert {sanierung}" if sanierung else ""
    desc = (
        f"Living context for {lie.get('name', lie_id)} ({lie_id}, "
        f"{lie.get('plz', '')} {lie.get('ort', '')}). Baujahr {lie.get('baujahr', '?')}"
        f"{sanierung_part}. {len(gebaeude)} buildings ({haus_refs}), {len(einheiten)} units, "
        f"{len(eigentuemer)} owners, {len(mieter)} tenants, {len(dienstleister)} service "
        f"providers. Verwalter {lie.get('verwalter', '?')}. WEG-Konto "
        f"{lie.get('weg_bankkonto_bank', '?')}, Verwalter-Konto "
        f"{lie.get('verwalter_bank', '?')}. First stop for ANY question about this "
        f"property — buildings, units, owners, tenants, service providers, finances, "
        f"ETV, BKA, Hausgeld, Rücklage, Wirtschaftsplan, Beschlüsse, contractor "
        f"relationships. Routes to detail via 02_buildings/, 03_people/, "
        f"04_dienstleister/, 05_finances/, 06_skills.md, 07_timeline.md."
    )
    out = [_frontmatter(name, desc)]

    out.append(f"# {lie.get('name', lie_id)} — Living Context\n\n")
    out.append(
        f"> 1 Verwalter, {len(gebaeude)} Häuser, {len(einheiten)} Einheiten, "
        f"{len(eigentuemer)} Eigentümer, {len(mieter)} Mieter, "
        f"{len(dienstleister)} Dienstleister. WEG-Konto "
        f"{lie.get('weg_bankkonto_bank', '?')}, Rücklage at separate IBAN.\n\n"
    )
    out.append(
        "**See also:** @05_finances/overview.md · @06_skills.md · @07_timeline.md · @log.md\n\n"
    )

    rows = ["| ID | Hausnr | Units | Stories | Elevator |", "|---|---|---|---|---|"]
    for g in gebaeude:
        rows.append(
            f"| {g['id']} | {g.get('hausnr', '')} | {g.get('einheiten', '')} | "
            f"{g.get('etagen', '')} | {'yes' if g.get('fahrstuhl') else 'no'} |"
        )
    out.append(_section("Buildings", "\n".join(rows)))

    weg_iban = lie.get("weg_bankkonto_iban", "")
    weg_bank = lie.get("weg_bankkonto_bank", "")
    verwalter_iban = lie.get("verwalter_iban", "")
    verwalter_bank = lie.get("verwalter_bank", "")
    bank_bullets = [
        _bullet(f"WEG-Konto: `{weg_iban}` ({weg_bank})"),
        _bullet(f"Rücklage: `{lie.get('ruecklage_iban', '')}`"),
        _bullet(f"Verwalter: `{verwalter_iban}` ({verwalter_bank})"),
    ]
    out.append(_section("Bank Accounts", "".join(bank_bullets).rstrip()))

    out.append(
        _section(
            "Open Issues",
            _agent_managed_comment("keyed bullets, format `- 🔴 **EH-XX:** ... [^source]`"),
        )
    )
    out.append(
        _section(
            "Recent Events",
            _agent_managed_comment("ring buffer max=50, prepend rows, older → 07_timeline.md"),
        )
    )
    out.append(
        _section(
            "Procedural Memory",
            _agent_managed_comment("one bullet per skill, link to @06_skills.md"),
        )
    )
    out.append(_section("Provenance", _agent_managed_comment("footnote definitions only")))

    out.append(_human_notes_footer())
    return "".join(out)


def render_lie_state(stammdaten: dict[str, Any]) -> dict[str, Any]:
    lie = stammdaten["liegenschaft"]
    return {
        "schema_version": 1,
        "property_id": lie["id"],
        "bootstrapped_at": datetime.now(UTC).isoformat(),
        "last_patched": None,
        "counts": {
            "buildings": len(stammdaten.get("gebaeude", [])),
            "units": len(stammdaten.get("einheiten", [])),
            "owners": len(stammdaten.get("eigentuemer", [])),
            "tenants": len(stammdaten.get("mieter", [])),
            "dienstleister": len(stammdaten.get("dienstleister", [])),
            "open_issues": 0,
        },
    }


def render_log(stammdaten: dict[str, Any] | None = None) -> str:
    lie = (stammdaten or {}).get("liegenschaft", {})
    lie_id = lie.get("id", "this property")
    desc = (
        f"Event log for {lie_id} ({lie.get('name', '')}). Append-only chronological "
        f"record of ingests, queries, lint passes, conflict resolutions, and human "
        f"edits. Each entry begins `## [<iso-date>] <kind> | <summary>` so it stays "
        f"grep-parseable: `grep '^## \\[' log.md | tail -20` returns the last 20 "
        f"events. Read for timeline reconstruction, recent-activity context, audit "
        f"trail, or to seed Hermes loop replay."
    )
    return (
        _frontmatter("property-log", desc)
        + _agent_managed_comment("append-only; each entry is `## [<iso>] <kind> | <summary>`")
        + "\n"
        + _human_notes_footer()
    )


def render_skills(stammdaten: dict[str, Any] | None = None) -> str:
    lie = (stammdaten or {}).get("liegenschaft", {})
    lie_id = lie.get("id", "this property")
    desc = (
        f"Procedural memory for {lie_id} ({lie.get('name', '')}) — one ## entry per "
        f"extracted skill, each with its own skills.md frontmatter (name + "
        f"description). The Linter Hermes inner loop writes here when "
        f"complexity_score > 5 or when a multi-step trajectory recurs. Read for "
        f"repeated procedures specific to this property: heating-emergency-after-hours, "
        f"verwalterbeschluss-lookup, rechnungsfreigabe-flow, mahnung-eskalation, "
        f"ETV-vorbereitung, BKA-quartalslauf. Cross-references DL-, MIE-, EIG- "
        f"entities mentioned in trigger conditions."
    )
    return _frontmatter("property-skills", desc) + _human_notes_footer()


def render_timeline(stammdaten: dict[str, Any] | None = None) -> str:
    lie = (stammdaten or {}).get("liegenschaft", {})
    lie_id = lie.get("id", "this property")
    n_haus = len((stammdaten or {}).get("gebaeude", []))
    desc = (
        f"Full chronology for {lie_id} ({lie.get('name', '')}) — overflow from "
        f"`Recent Events` ring buffers across the Liegenschaft, all {n_haus} "
        f"buildings, every unit, owner, tenant, and service provider. Append-only, "
        f"oldest at bottom. Read when reconstructing history beyond the last 50 "
        f"events of any file, doing year-over-year comparison, preparing an ETV "
        f"report, or auditing an Eigentümer / Dienstleister relationship over time."
    )
    return (
        _frontmatter("property-timeline", desc)
        + _section("Events", _agent_managed_comment("append-only rows, oldest at bottom"))
        + _human_notes_footer()
    )


def render_pending_review(stammdaten: dict[str, Any] | None = None) -> str:
    lie = (stammdaten or {}).get("liegenschaft", {})
    lie_id = lie.get("id", "this property")
    desc = (
        f"Open conflicts for {lie_id} awaiting PM resolution. The Patcher writes "
        f"here when a new fact contradicts an existing keyed bullet/row (status flip, "
        f"date drift, amount delta), when a vocab/schema check fails, or when the "
        f"Hermes outer loop proposes a schema change. Each entry lists both claims, "
        f"both sources, timestamps, and the file/section affected. Resolve in-place "
        f"by editing or deleting the entry, or append `**Approved by:** <pm>` to "
        f"approve a schema proposal; the Linter clears resolved entries on next run. "
        f"Read daily during PM triage."
    )
    return (
        _frontmatter("pending-review", desc)
        + _section("Open Conflicts", _agent_managed_comment("one ### entry per conflict"))
        + _human_notes_footer()
    )


def render_finances_overview(stammdaten: dict[str, Any]) -> str:
    lie = stammdaten["liegenschaft"]
    lie_id = lie["id"]
    mieter = stammdaten.get("mieter", [])
    eigentuemer = stammdaten.get("eigentuemer", [])
    dienstleister = stammdaten.get("dienstleister", [])
    contracted = [d for d in dienstleister if d.get("vertrag_monatlich")]
    active = sum(1 for m in mieter if m.get("mietende") is None)
    monthly_contracts = sum(d.get("vertrag_monatlich") or 0 for d in contracted)
    desc = (
        f"Financial overview for {lie_id} ({lie.get('name', '')}). Three operating "
        f"bank accounts: WEG-Konto at {lie.get('weg_bankkonto_bank', '?')}, Rücklage "
        f"(separate IBAN), Verwalter-Konto at {lie.get('verwalter_bank', '?')}. "
        f"{active} active tenancies, {len(eigentuemer)} owners on Hausgeld plan, "
        f"{len(contracted)} contracted dienstleister (€{monthly_contracts:.0f}/month "
        f"baseline). Read for high-level finance state. Drill into reconciliation.md "
        f"for bank ⋈ invoice anomalies, invoices/<YYYY-MM>/ for individual Rechnungen. "
        f"For per-tenant payment history, route to 03_people/mieter/MIE-XX.md; for "
        f"per-owner Hausgeld ledger, route to 03_people/eigentuemer/EIG-XX.md."
    )
    bullets = [
        _bullet(f"WEG-Konto IBAN: `{lie.get('weg_bankkonto_iban', '')}`"),
        _bullet(f"Rücklage IBAN: `{lie.get('ruecklage_iban', '')}`"),
        _bullet(f"Verwalter IBAN: `{lie.get('verwalter_iban', '')}`"),
        _bullet(f"Active tenancies: {active}"),
        _bullet(f"Contracted dienstleister: {len(contracted)}"),
    ]
    return (
        _frontmatter("finances-overview", desc)
        + _section("Overview", "".join(bullets).rstrip())
        + _human_notes_footer()
    )


def render_finances_reconciliation(stammdaten: dict[str, Any] | None = None) -> str:
    lie = (stammdaten or {}).get("liegenschaft", {})
    lie_id = lie.get("id", "this property")
    desc = (
        f"Reconciliation report for {lie_id} — bank tx ⋈ invoices ⋈ stammdaten with "
        f"seeded anomalies from data/bank/error_types. Surfaces wrong IBAN, missing "
        f"reference, duplicates, amount mismatches, orphan transactions, and "
        f"Buchungsfehler. One row per anomaly, latest at top. Read when investigating "
        f"a payment dispute, doing month-end close, preparing the BKA, or auditing a "
        f"Dienstleister Rechnungslauf. Cross-references DL-XXX (payee), INV-XXXXX "
        f"(invoice source), TX-XXXXX (bank transaction)."
    )
    return (
        _frontmatter("finances-reconciliation", desc)
        + _section("Anomalies", _agent_managed_comment("one row per anomaly, table form"))
        + _human_notes_footer()
    )


def render_haus_index(haus: dict[str, Any], stammdaten: dict[str, Any]) -> str:
    haus_id = haus["id"]
    einheiten = _einheiten_for_haus(haus_id, stammdaten.get("einheiten", []))
    lie = stammdaten.get("liegenschaft", {})
    lie_id = lie.get("id", "")
    eh_ids = sorted(e["id"] for e in einheiten)
    if len(eh_ids) > 1:
        eh_range = f"{eh_ids[0]}..{eh_ids[-1]}"
    elif eh_ids:
        eh_range = eh_ids[0]
    else:
        eh_range = "no units"
    desc = (
        f"Building {haus_id} (Hausnr {haus.get('hausnr', '')}) of "
        f"{lie.get('name', lie_id)} (parent {lie_id}). {haus.get('einheiten', '')} "
        f"apartments {eh_range}, Baujahr {haus.get('baujahr', '?')}, "
        f"{haus.get('etagen', '?')} Etagen, "
        f"{'with' if haus.get('fahrstuhl') else 'no'} Fahrstuhl. Use for "
        f"building-specific questions: physical state, roof, façade, heating, "
        f"building-wide repairs, fire safety (BetrSichV / DGUV V3), Wartung, "
        f"building-level tenant issues, Hausordnung, Schlüsselverwaltung. For "
        f"owner / finance / ETV / BKA / Hausgeld questions, route up to "
        f"{lie_id}/index.md. For unit-level tenancy or repair history, drill into "
        f"units/EH-XX.md."
    )
    summary_bullets = [
        _bullet(f"Hausnr: {haus.get('hausnr', '')}"),
        _bullet(f"Baujahr: {haus.get('baujahr', '')}"),
        _bullet(f"Etagen: {haus.get('etagen', '')}"),
        _bullet(f"Fahrstuhl: {'yes' if haus.get('fahrstuhl') else 'no'}"),
        _bullet(f"Einheiten: {haus.get('einheiten', '')}"),
    ]

    rows = ["| ID | WE-Nr | Lage | Typ | qm | Zimmer | MEA |", "|---|---|---|---|---|---|---|"]
    for e in einheiten:
        rows.append(
            f"| {e['id']} | {e.get('einheit_nr', '')} | {e.get('lage', '')} | "
            f"{e.get('typ', '')} | {e.get('wohnflaeche_qm', '')} | "
            f"{e.get('zimmer', '')} | {e.get('miteigentumsanteil', '')} |"
        )

    return (
        _frontmatter(f"building-{haus_id.lower()}", desc)
        + _section("Summary", "".join(summary_bullets).rstrip())
        + _section("Units", "\n".join(rows))
        + _section(
            "Open Issues",
            _agent_managed_comment("keyed bullets, format `- 🔴 **EH-XX:** ... [^source]`"),
        )
        + _section("Recent Events", _agent_managed_comment("ring buffer max=50"))
        + _section("Contractors Active", _agent_managed_comment("one bullet per active DL"))
        + _section("Provenance", _agent_managed_comment("footnote definitions only"))
        + _human_notes_footer()
    )


def render_einheit(einheit: dict[str, Any], stammdaten: dict[str, Any]) -> str:
    eh_id = einheit["id"]
    haus_id = einheit.get("haus_id", "")
    mieter = _mieter_for_einheit(eh_id, stammdaten.get("mieter", []))
    eig = _eigentuemer_for_einheit(eh_id, stammdaten.get("eigentuemer", []))
    lie = stammdaten.get("liegenschaft", {})
    lie_id = lie.get("id", "")

    if mieter is not None:
        mie_full = " ".join(filter(None, [mieter.get("vorname"), mieter.get("nachname")])).strip()
        tenant_part = (
            f"Current tenant {mieter['id']}"
            f"{f' {mie_full}' if mie_full else ''} "
            f"(Mietbeginn {mieter.get('mietbeginn', '?')}, Kaltmiete "
            f"€{mieter.get('kaltmiete', '?')}). "
        )
    elif eig is not None and eig.get("selbstnutzer"):
        tenant_part = "Selbstnutzer (kein externer Mieter). "
    else:
        tenant_part = "Currently leerstehend. "

    if eig is not None:
        eig_full = " ".join(filter(None, [eig.get("vorname"), eig.get("nachname")])).strip()
        owner_part = (
            f"Owner {eig['id']}"
            f"{f' {eig_full}' if eig_full else ''}"
            f"{' (Beirat)' if eig.get('beirat') else ''}"
            f"{' (SEV-Mandat)' if eig.get('sev_mandat') else ''}. "
        )
    else:
        owner_part = "Owner unknown. "

    cross_refs = []
    if eig:
        cross_refs.append(f"{eig['id']} (owner)")
    if mieter:
        cross_refs.append(f"{mieter['id']} (tenant)")
    cross_part = f" Cross-references {' and '.join(cross_refs)}." if cross_refs else ""
    desc = (
        f"Apartment {eh_id} ({einheit.get('einheit_nr', '')}, "
        f"{einheit.get('lage', '')}) in {haus_id} ({lie.get('name', lie_id)}). "
        f"{einheit.get('wohnflaeche_qm', '?')} m², {einheit.get('zimmer', '?')} "
        f"Zimmer, MEA {einheit.get('miteigentumsanteil', '?')}. "
        f"{tenant_part}{owner_part}"
        f"Use for unit-specific history: tenancy timeline, repair tickets, payment "
        f"history, complaints, Wohnungsabnahme/-übergabe records, contact log."
        f"{cross_part} For building-wide context, route up to {haus_id}/index.md."
    )
    facts = [
        _bullet(f"ID: {eh_id}"),
        _bullet(f"Einheit-Nr: {einheit.get('einheit_nr', '')}"),
        _bullet(f"Lage: {einheit.get('lage', '')}"),
        _bullet(f"Typ: {einheit.get('typ', '')}"),
        _bullet(f"Wohnfläche: {einheit.get('wohnflaeche_qm', '')} m²"),
        _bullet(f"Zimmer: {einheit.get('zimmer', '')}"),
        _bullet(f"MEA: {einheit.get('miteigentumsanteil', '')}"),
    ]

    if mieter is not None:
        tenant_body = _bullet(f"See [{mieter['id']}](../../../03_people/mieter/{mieter['id']}.md)")
    elif eig is not None and eig.get("selbstnutzer"):
        tenant_body = _bullet("(none — selbstnutzer)")
    else:
        tenant_body = _bullet("(none)")

    if eig is not None:
        owner_body = _bullet(f"See [{eig['id']}](../../../03_people/eigentuemer/{eig['id']}.md)")
    else:
        owner_body = _bullet("(unknown)")

    return (
        _frontmatter(f"unit-{eh_id.lower()}", desc)
        + _section("Unit Facts", "".join(facts).rstrip())
        + _section("Current Tenant", tenant_body.rstrip())
        + _section("Current Owner", owner_body.rstrip())
        + _section("History", _agent_managed_comment("prepend rows, ring buffer"))
        + _section("Provenance", _agent_managed_comment("footnote definitions only"))
        + _human_notes_footer()
    )


def render_eigentuemer(eig: dict[str, Any], stammdaten: dict[str, Any]) -> str:
    eig_id = eig["id"]
    einheiten = stammdaten.get("einheiten", [])
    lie = stammdaten.get("liegenschaft", {})
    lie_id = lie.get("id", "")
    full_name = " ".join(filter(None, [eig.get("vorname"), eig.get("nachname")])) or eig.get(
        "firma", ""
    )
    owned_ids = eig.get("einheit_ids") or []
    owned_haeuser = sorted({_haus_for_einheit(eh, einheiten) for eh in owned_ids} - {None})
    multi_haus = len(owned_haeuser) > 1
    if multi_haus:
        haus_part = f" across {len(owned_haeuser)} buildings ({', '.join(owned_haeuser)})"
    elif owned_haeuser:
        haus_part = f" in {owned_haeuser[0]}"
    else:
        haus_part = ""
    role_flags = ", ".join(
        flag
        for flag, on in [
            ("Beirat", eig.get("beirat")),
            ("SEV-Mandat", eig.get("sev_mandat")),
            ("Selbstnutzer", eig.get("selbstnutzer")),
        ]
        if on
    )
    role_part = f" Roles: {role_flags}." if role_flags else ""
    desc = (
        f"Eigentümer {eig_id} ({full_name}) of {lie.get('name', lie_id)} ({lie_id}). "
        f"Owns {len(owned_ids)} unit(s) ({', '.join(owned_ids) or 'none'}){haus_part}."
        f"{role_part} Email {eig.get('email', '?')}, IBAN "
        f"`{eig.get('iban', '?')}`. Use for owner-specific queries: contact, unit "
        f"list, Hausgeld payment history, ETV/Beschluss correspondence, "
        f"Sondereigentumsverwaltung-Mandat status, "
        f"{'Beirat decisions, ' if eig.get('beirat') else ''}"
        f"{'multi-building cross-references, ' if multi_haus else ''}"
        f"Mahnung-Historie. For per-unit detail, drill into the linked EH-XX.md files."
    )
    contact = [
        _bullet(f"{eig.get('anrede', '')} {full_name}".strip()),
        _bullet(f"Email: {eig.get('email', '')}"),
        _bullet(f"Telefon: {eig.get('telefon', '')}"),
        _bullet(f"Adresse: {eig.get('strasse', '')}, {eig.get('plz', '')} {eig.get('ort', '')}"),
        _bullet(f"IBAN: `{eig.get('iban', '')}`"),
    ]

    units = []
    for eh_id in eig.get("einheit_ids") or []:
        haus = _haus_for_einheit(eh_id, einheiten) or "UNKNOWN"
        units.append(_bullet(f"[{eh_id}](../../02_buildings/{haus}/units/{eh_id}.md)"))
    units_body = "".join(units).rstrip() if units else _bullet("(none)").rstrip()

    roles = [
        _bullet(f"selbstnutzer: {bool(eig.get('selbstnutzer'))}"),
        _bullet(f"sev_mandat: {bool(eig.get('sev_mandat'))}"),
        _bullet(f"beirat: {bool(eig.get('beirat'))}"),
    ]

    return (
        _frontmatter(f"owner-{eig_id.lower()}", desc)
        + _section("Contact", "".join(contact).rstrip())
        + _section("Units Owned", units_body)
        + _section("Roles", "".join(roles).rstrip())
        + _section("Payment History", _agent_managed_comment("ring buffer max=12 months"))
        + _section("Correspondence Summary", _agent_managed_comment("ring buffer"))
        + _section("Provenance", _agent_managed_comment("footnote definitions only"))
        + _human_notes_footer()
    )


def render_mieter(mie: dict[str, Any], stammdaten: dict[str, Any]) -> str:
    mie_id = mie["id"]
    einheit_id = mie.get("einheit_id", "")
    eig_id = mie.get("eigentuemer_id", "")
    haus_id = _haus_for_einheit(einheit_id, stammdaten.get("einheiten", [])) or "UNKNOWN"
    lie = stammdaten.get("liegenschaft", {})
    lie_id = lie.get("id", "")
    full_name = " ".join(filter(None, [mie.get("vorname"), mie.get("nachname")]))
    mietende = mie.get("mietende")
    mietende_part = f"Mietende {mietende}" if mietende else "Mietverhältnis aktiv"
    desc = (
        f"Mieter {mie_id} ({full_name}) in {einheit_id} ({haus_id}, "
        f"{lie.get('name', lie_id)}). Mietbeginn {mie.get('mietbeginn', '?')}, "
        f"{mietende_part}. Kaltmiete €{mie.get('kaltmiete', '?')}, "
        f"NK-Vorauszahlung €{mie.get('nk_vorauszahlung', '?')}, "
        f"Kaution €{mie.get('kaution', '?')}. Vermieter (Eigentümer) {eig_id}. "
        f"Email {mie.get('email', '?')}, IBAN `{mie.get('iban', '?')}`. "
        f"Use for tenant-specific queries: contact, tenancy terms, Mietzahlungen, "
        f"Nebenkostenabrechnung-Historie, Reparaturanfragen, Beschwerden, "
        f"Mahnung-Eskalation, Mietminderung, Kündigung-Schritte. For unit-level "
        f"context (Wohnungsgröße, Lage, Vorgeschichte) drill into "
        f"02_buildings/{haus_id}/units/{einheit_id}.md."
    )
    contact = [
        _bullet(f"{mie.get('anrede', '')} {full_name}".strip()),
        _bullet(f"Email: {mie.get('email', '')}"),
        _bullet(f"Telefon: {mie.get('telefon', '')}"),
        _bullet(f"IBAN: `{mie.get('iban', '')}`"),
    ]

    tenancy = [
        _bullet(f"Einheit: [{einheit_id}](../../02_buildings/{haus_id}/units/{einheit_id}.md)"),
        _bullet(f"Eigentümer: [{eig_id}](../eigentuemer/{eig_id}.md)"),
        _bullet(f"Mietbeginn: {mie.get('mietbeginn', '')}"),
        _bullet(f"Mietende: {mie.get('mietende') or 'open'}"),
        _bullet(f"Kaltmiete: {mie.get('kaltmiete', '')} €"),
        _bullet(f"NK-Vorauszahlung: {mie.get('nk_vorauszahlung', '')} €"),
        _bullet(f"Kaution: {mie.get('kaution', '')} €"),
    ]

    return (
        _frontmatter(f"tenant-{mie_id.lower()}", desc)
        + _section("Contact", "".join(contact).rstrip())
        + _section("Tenancy", "".join(tenancy).rstrip())
        + _section("Payment History", _agent_managed_comment("ring buffer max=12 months"))
        + _section("Contact History", _agent_managed_comment("ring buffer"))
        + _section("Provenance", _agent_managed_comment("footnote definitions only"))
        + _human_notes_footer()
    )


def render_dienstleister(dl: dict[str, Any], stammdaten: dict[str, Any]) -> str:
    dl_id = dl["id"]
    lie = stammdaten.get("liegenschaft", {})
    lie_id = lie.get("id", "")
    monthly = dl.get("vertrag_monatlich")
    rate = dl.get("stundensatz")
    contract_part = (
        f"Monatlicher Vertrag €{monthly:.0f}. " if monthly else "Auftragsbasis (kein Vertrag). "
    )
    rate_part = f"Stundensatz €{rate:.0f}. " if rate else ""
    desc = (
        f"Dienstleister {dl_id} ({dl.get('firma', '')}, {dl.get('branche', '')}) "
        f"contracted by {lie.get('name', lie_id)} ({lie_id}). Ansprechpartner "
        f"{dl.get('ansprechpartner', '?')}, Email {dl.get('email', '?')}, "
        f"Telefon {dl.get('telefon', '?')}. {contract_part}{rate_part}"
        f"IBAN `{dl.get('iban', '?')}`, USt-ID {dl.get('ust_id', '?')}. "
        f"Use for service-provider queries: scope (Branche {dl.get('branche', '?')}), "
        f"Verträge, Rechnungen, Wartungs-Intervalle, Notdienst-Eligibility, "
        f"Performance-Notes, Eskalation, Reklamationen, Zahlungsfreigabe-Historie. "
        f"For finance-side reconciliation, route to 05_finances/reconciliation.md."
    )
    services = [
        _bullet(f"Firma: {dl.get('firma', '')}"),
        _bullet(f"Branche: {dl.get('branche', '')}"),
        _bullet(f"Ansprechpartner: {dl.get('ansprechpartner', '')}"),
        _bullet(f"Email: {dl.get('email', '')}"),
        _bullet(f"Telefon: {dl.get('telefon', '')}"),
        _bullet(f"Adresse: {dl.get('strasse', '')}, {dl.get('plz', '')} {dl.get('ort', '')}"),
        _bullet(f"IBAN: `{dl.get('iban', '')}`"),
        _bullet(f"USt-ID: {dl.get('ust_id', '')}"),
    ]

    contracts = [
        _bullet(f"Vertrag monatlich: {dl.get('vertrag_monatlich') or '—'} €"),
        _bullet(f"Stundensatz: {dl.get('stundensatz') or '—'} €"),
    ]

    return (
        _frontmatter(f"dienstleister-{dl_id.lower()}", desc)
        + _section("Services", "".join(services).rstrip())
        + _section("Contracts", "".join(contracts).rstrip())
        + _section("Recent Invoices", _agent_managed_comment("table, prepend rows"))
        + _section("Performance Notes", _agent_managed_comment("ring buffer"))
        + _section("Provenance", _agent_managed_comment("footnote definitions only"))
        + _human_notes_footer()
    )
