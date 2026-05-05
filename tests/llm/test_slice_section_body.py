from __future__ import annotations

from app.services.locate import slice_section_body


def test_short_body_passes_through_unchanged() -> None:
    body = "Short prose. Heizung defekt seit Mittwoch.\n"
    assert slice_section_body(body) == body


def test_keyed_section_keeps_keyed_lines_and_elides_prose() -> None:
    body = (
        "## Open Issues\n"
        "\n"
        "Some intro paragraph that is irrelevant to the patcher and pads the body "
        "with prose noise. " * 12 + "\n"
        "- 🔴 **EH-014:** Heating outage [^EMAIL-12044]\n"
        "- 🟡 **EH-015:** Window draft [^EMAIL-12045]\n"
        "- 🟢 **EH-016:** Resolved 2026-04-22 [^EMAIL-12030]\n"
        "\n"
        "Long trailing prose that nobody needs in the patch context. " * 10
    )
    sliced = slice_section_body(body)
    assert "**EH-014:**" in sliced
    assert "**EH-015:**" in sliced
    assert "**EH-016:**" in sliced
    assert "Some intro paragraph" not in sliced
    assert "Long trailing prose" not in sliced
    assert "elided" in sliced
    assert len(sliced) < len(body)


def test_table_rows_are_kept() -> None:
    body = (
        "## Recent Events\n" + "Padding paragraph. " * 50 + "\n"
        "| Date | Type | Summary | Source |\n"
        "|---|---|---|---|\n"
        "| 2026-04-25 | email | EH-014 heating | [^EMAIL-12044] |\n"
        "| 2026-04-24 | bank  | rent payment   | [^TX-9001]    |\n"
    )
    sliced = slice_section_body(body)
    assert "| 2026-04-25 | email" in sliced
    assert "| 2026-04-24 | bank" in sliced
    assert "Padding paragraph" not in sliced


def test_footnote_definitions_are_kept() -> None:
    body = (
        "Body intro paragraph. " * 60 + "\n"
        "[^EMAIL-12044]: normalize/eml/2026-04/EMAIL-12044.md\n"
        "[^EMAIL-12045]: normalize/eml/2026-04/EMAIL-12045.md\n"
    )
    sliced = slice_section_body(body)
    assert "[^EMAIL-12044]:" in sliced
    assert "[^EMAIL-12045]:" in sliced


def test_prose_only_section_falls_back_to_head_and_tail() -> None:
    body = "alpha " * 200 + "MIDDLE " * 50 + "omega " * 100
    sliced = slice_section_body(body)
    assert sliced.startswith("alpha")
    assert sliced.endswith("omega ".strip()) or sliced.rstrip().endswith("omega")
    assert "MIDDLE" not in sliced
    assert "elided" in sliced
    assert len(sliced) < len(body)


def test_keyed_line_with_hauf_id_pattern_kept() -> None:
    body = (
        "## Buildings\n"
        + "\n".join(["filler line"] * 80)
        + "\n- **HAUS-12:** 24 units, last inspection 2025-08\n"
    )
    sliced = slice_section_body(body)
    assert "**HAUS-12:**" in sliced
    assert "filler line" not in sliced or sliced.count("filler line") < 80
