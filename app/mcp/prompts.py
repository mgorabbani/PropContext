from __future__ import annotations

from fastmcp import FastMCP


def register_prompts(mcp: FastMCP) -> None:
    @mcp.prompt(
        name="summarize_property",
        description="Summarize the current state of a property in plain language.",
    )
    def summarize_property(property_id: str) -> str:
        return (
            f"You are a Berlin property management assistant. Read the resource "
            f"`property://{property_id}` and summarize: open issues, recent maintenance, "
            f"compliance status, and any owner/tenant items needing follow-up. "
            f"Be concise. Cite section headings."
        )

    @mcp.prompt(
        name="compliance_check",
        description="Run a German legal compliance check on a building.",
    )
    def compliance_check(property_id: str, building_id: str) -> str:
        return (
            f"Read `building://{property_id}/{building_id}`. Cross-check against WEG, "
            f"BauO Bln, BetrSichV obligations. List: (1) overdue items, (2) upcoming "
            f"deadlines in next 90 days, (3) missing documentation. Answer in German "
            f"if the source is in German."
        )
