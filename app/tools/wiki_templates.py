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
    lie_id = lie["id"]
    name = f"property-{lie_id.lower()}"
    desc = (
        f"Property {lie_id} ({lie.get('name', '')}, {lie.get('strasse', '')}, "
        f"{lie.get('plz', '')} {lie.get('ort', '')}). Read first for any agent task "
        f"touching this Liegenschaft. Lists buildings, bank accounts, open issues, "
        f"recent events, and procedural memory. Drill into 02_buildings/ for per-building "
        f"detail, 03_people/ for owners and tenants, 04_dienstleister/ for contractors."
    )
    out = [_frontmatter(name, desc)]

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


def render_log() -> str:
    desc = (
        "Property event log. Append-only chronological record of ingests, queries, "
        "lint passes. Each entry begins `## [<iso-date>] <kind> | <summary>`."
    )
    return (
        _frontmatter("property-log", desc)
        + _section("Log", _agent_managed_comment("append-only, one ## entry per event"))
        + _human_notes_footer()
    )


def render_skills() -> str:
    desc = (
        "Procedural memory for this property — one ## entry per extracted skill, each "
        "with its own skills.md frontmatter (name + description). The Linter Hermes "
        "inner loop writes here when complexity_score > 5. Read for repeated procedures "
        "(e.g. heating-emergency-after-hours, verwalterbeschluss-lookup)."
    )
    return _frontmatter("property-skills", desc) + _human_notes_footer()


def render_timeline() -> str:
    desc = (
        "Full chronology of this property — overflow from Recent Events ring buffers "
        "across all files. Append-only. Read when reconstructing history beyond the "
        "last 50 events."
    )
    return (
        _frontmatter("property-timeline", desc)
        + _section("Events", _agent_managed_comment("append-only rows, oldest at bottom"))
        + _human_notes_footer()
    )


def render_pending_review() -> str:
    desc = (
        "Open conflicts awaiting PM resolution. The Patcher writes here when a new fact "
        "contradicts an existing keyed bullet/row, or when a vocab/schema check fails. "
        "Each entry lists both claims, both sources, timestamps. Resolve in-place; the "
        "Linter clears resolved entries on next run."
    )
    return (
        _frontmatter("pending-review", desc)
        + _section("Open Conflicts", _agent_managed_comment("one ### entry per conflict"))
        + _human_notes_footer()
    )


def render_finances_overview(stammdaten: dict[str, Any]) -> str:
    lie = stammdaten["liegenschaft"]
    mieter = stammdaten.get("mieter", [])
    dienstleister = stammdaten.get("dienstleister", [])
    contracted = [d for d in dienstleister if d.get("vertrag_monatlich")]
    desc = (
        f"Financial overview for {lie['id']}. Lists the three operating bank accounts "
        f"and high-level counts (active tenancies, contracted dienstleister)."
    )
    bullets = [
        _bullet(f"WEG-Konto IBAN: `{lie.get('weg_bankkonto_iban', '')}`"),
        _bullet(f"Rücklage IBAN: `{lie.get('ruecklage_iban', '')}`"),
        _bullet(f"Verwalter IBAN: `{lie.get('verwalter_iban', '')}`"),
        _bullet(f"Active tenancies: {sum(1 for m in mieter if m.get('mietende') is None)}"),
        _bullet(f"Contracted dienstleister: {len(contracted)}"),
    ]
    return (
        _frontmatter("finances-overview", desc)
        + _section("Overview", "".join(bullets).rstrip())
        + _human_notes_footer()
    )


def render_finances_reconciliation() -> str:
    desc = (
        "Reconciliation report — bank tx ⋈ invoices ⋈ stammdaten with seeded anomalies "
        "from data/bank/error_types. Read to surface wrong IBAN, missing reference, "
        "duplicates, amount mismatches."
    )
    return (
        _frontmatter("finances-reconciliation", desc)
        + _section("Anomalies", _agent_managed_comment("one row per anomaly, table form"))
        + _human_notes_footer()
    )


def render_haus_index(haus: dict[str, Any], stammdaten: dict[str, Any]) -> str:
    haus_id = haus["id"]
    einheiten = _einheiten_for_haus(haus_id, stammdaten.get("einheiten", []))
    desc = (
        f"Building {haus_id} (Hausnr {haus.get('hausnr', '')}) — "
        f"{haus.get('einheiten', '')} units across {haus.get('etagen', '')} floors, "
        f"{'with' if haus.get('fahrstuhl') else 'no'} elevator. Read for unit "
        f"overviews, open issues affecting this building, recent events, and "
        f"contractors currently working here."
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
    desc = (
        f"Unit {eh_id} ({einheit.get('einheit_nr', '')}, {einheit.get('lage', '')}) "
        f"in {haus_id} — {einheit.get('wohnflaeche_qm', '')} m², "
        f"{einheit.get('zimmer', '')} rooms. Read for current tenancy, ownership, "
        f"and unit-specific issue history."
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
    full_name = " ".join(filter(None, [eig.get("vorname"), eig.get("nachname")])) or eig.get(
        "firma", ""
    )
    desc = (
        f"Owner {eig_id} ({full_name}). Owns "
        f"{len(eig.get('einheit_ids') or [])} unit(s). "
        f"{'Beirat. ' if eig.get('beirat') else ''}"
        f"{'SEV-Mandat. ' if eig.get('sev_mandat') else ''}"
        f"{'Selbstnutzer. ' if eig.get('selbstnutzer') else ''}"
        f"Read for owner contact, unit list, payment history, correspondence."
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
    full_name = " ".join(filter(None, [mie.get("vorname"), mie.get("nachname")]))
    desc = (
        f"Tenant {mie_id} ({full_name}) in {einheit_id} (building {haus_id}). "
        f"Mietbeginn {mie.get('mietbeginn', '')}, Kaltmiete "
        f"{mie.get('kaltmiete', '')}€. Read for contact, tenancy terms, "
        f"payment history, contact history."
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
    del stammdaten
    dl_id = dl["id"]
    desc = (
        f"Dienstleister {dl_id} ({dl.get('firma', '')}, {dl.get('branche', '')}). "
        f"Contact: {dl.get('ansprechpartner', '')}. "
        f"{'Monthly contract. ' if dl.get('vertrag_monatlich') else ''}"
        f"Read for service scope, contracts, recent invoices, performance notes."
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
