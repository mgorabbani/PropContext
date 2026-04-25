🏢 Building-as-Code (BaC): The Hermes-Wiki Engine for Buena

Technical Overview

This repository implements an autonomous engine designed for the Buena Challenge. It transforms scattered property context (ERPs, PDFs, Emails, Slack) into a single, high-density, self-updating building.md file.

By combining Andrej Karpathy’s LLM Wiki pattern with the Hermes Agent self-improvement loop, we move beyond simple search-based RAG to a "Learning State" property management system.

🏗️ Architecture: The Hermes Self-Improvement Loop

The engine implements the 6-step recursive loop used by the Hermes Agent to ensure the building.md file (the "Procedural Memory") grows more intelligent with every interaction.

1. Task Execution (Aufgabe ausführen)

When a request comes in (e.g., "A tenant in Apt 4 reports a leak"), the agent performs tool calls:

Querying the ERP for tenant history.

Searching Gmail for previous contractor invoices.

Checking Slack for recent building-wide notices.

2. The Complexity Threshold (Komplexitätscheck)

Logic: If the task requires > 5 Tool Calls (as specified in the Hermes architecture), it is flagged as "Complex."

Action: Instead of just finishing the task, the agent identifies this as a "Learning Opportunity." If it's a simple one-off fact, it is discarded from the skill-extraction pipeline.

3. Skill Creation & Refinement (Skill erstellen + verfeinern)

The agent analyzes the successful trajectory of the complex task.

It synthesizes a new Procedural Skill (e.g., "Workflow: Handling Plumbing Emergencies in Building A").

This is drafted into a structured format, refining existing entries if a similar workflow exists.

4. Persist to Memory (In Memory persistieren)

The refined skill is "Surgically Injected" into the building.md file under the # Procedural Memory section.

High-density facts are updated in the # Physical State section with full provenance ([^Source]).

5. Periodic Nudge (Interne Anstöße)

The "Internal Alarm": The system doesn't just wait for user input. It runs background "Nudges" to:

Reconcile: Scan for contradictions (e.g., "Contract says maintenance is monthly, but logs show it hasn't happened in 60 days").

Synthesize: Merge small, fragmented updates into cohesive building summaries.

Alert: Nudge the Property Manager if a critical fact in the building.md has expired or reached a low confidence score.

6. User-Modeling (Nutzer-Modellierung)

The agent tracks how the Property Manager interacts with the building.md.

Preference Learning: If the manager consistently moves "Emergency Contacts" to the top, the agent updates its internal style.md to ensure all future buildings follow this layout.

Tone Alignment: It learns to prioritize the specific data points the user cares about (e.g., cost-efficiency vs. speed of repair).

📝 The building.md Schema (Knowledge State)

The output is a structured Markdown file that acts as the "Source of Truth" for any other AI agent.

# [Property ID] - Living Context

## 📊 Core Metadata
- **Owner:** ...
- **Risk Profile:** High (due to aging boiler [^GMAIL-88])

## 📜 Procedural Memory (Skills Learned via Hermes Loop)
- **Emergency Escalation:** "For leaks after 6 PM, call [Contractor X]. They have the master fob." (Extracted after a 7-step resolution event on 2024-03-01)

## 🛠️ Physical State & Facts
- **Keybox:** 5543 [Updated 2024-03-10 via Slack]
- **HVAC:** Filter changed 2024-01-15 [^PDF-12]

## 🔗 Provenance & Audit Trail
[^GMAIL-88]: Email Thread "Boiler Issues"
[^PDF-12]: Maintenance_Log_Q1.pdf


💉 Surgical Update Strategy (The "Novelty")

To preserve human edits, we use a Markdown AST (Abstract Syntax Tree) merge:

Parse: building.md -> JSON AST.

Diff: New Fact vs. Current State.

Verify: Check against User-Modeling rules (Does this update break a user-preferred format?).

Merge: Injected without overwriting manual notes.

🛠️ Stack Suggestion

LLM: gemini-2.5-flash for high-speed ingestion; Hermes-3-Llama-3.1 for the "Skill Extraction" reasoning.

Workflow: Python (FastAPI) + marko (AST Parsing) + SQLite (Source Indexing).

🎯 Hackathon Goals

MVP: Successful extraction of a "Skill" into Markdown after a simulated >5 step tool-use chain.

Stretch: Trigger a "Periodic Nudge" that detects an outdated fact and asks for confirmation.