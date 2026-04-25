🏢 Building-as-Code (BaC): The Hermes-Wiki Engine for Buena

Technical Overview

This repository implements an autonomous engine designed for the Buena Challenge. It transforms scattered property context (ERPs, PDFs, Emails, Slack) into a single, high-density, self-updating building.md file.

By combining Andrej Karpathy’s LLM Wiki pattern with the Hermes Agent self-improving logic, we move beyond simple search-based RAG to a "State-based" property management system.

🏗️ Architecture: The Synthesis Pipeline

The engine operates on a continuous loop of ingestion, reconciliation, and compression.

1. The Ingestion Layer (Multimodal Connectors)

Sources: Gmail (API), Slack (Webhooks), ERP (Database exports), and PDFs (LLM-based OCR).

Extraction: Every new piece of data is treated as an "event" containing facts, entities, and temporal context.

2. The Hermes "Researcher" Agent

Instead of just "storing" data, the Hermes-inspired agent performs three roles:

Fact Reconciler: If a new email says "Boiler fixed," but building.md says "Boiler broken," the agent updates the state and moves the old status to a # History sub-section.

Provenance Tracker: Every line written to the Markdown file is appended with a source hash/link (e.g., [^GMAIL-123]) to ensure auditability.

Skill Discovery: If a specific workflow (e.g., "how to access the roof in Building A") is discovered in a Slack thread, the agent extracts it as a Procedural Instruction.

📝 The building.md Schema

The output is a structured Markdown file that acts as the "Source of Truth" for any other AI agent.

# [Property Name/ID] - Context File

## 📊 Core Metadata
- **Address:** ...
- **Year Built:** ...
- **ERP-UID:** [Reference ID]

## 🛠️ Physical State (The "Living" Section)
- **Roof:** Last inspected 2024-01-10 [^PDF-44]
- **HVAC:** Centralized, maintenance due in 3 months.
- **Critical Codes:** [Keybox: 1234] (Update: 2024-02-15 via Slack)

## 📜 Procedural Memory (Hermes Extension)
- **Access Logic:** "To enter the basement, use the blue fob. If it fails, contact the super at..."
- **Tenant Handling:** "Tenants in Unit 4 prefer email over phone."

## 🔗 Provenance & History
[^PDF-44]: Google Drive / Surveys / Jan_Report.pdf
[^GMAIL-123]: thread_id_abc123 (Subject: Boiler Issue)


💉 Surgical Update Strategy (The "Novelty")

To prevent the LLM from destroying human edits or nuking important context, we use a Markdown AST (Abstract Syntax Tree) merge approach:

Parse: Convert current building.md into a JSON-based AST.

Propose: The Agent generates a "diff" based on new data (e.g., Update Section: Physical State -> Roof).

Validate: A secondary "Linter" LLM checks if the update contradicts existing "High-Confidence" facts.

Merge: The engine injects the new facts into the specific Markdown nodes while preserving manual human annotations.

🚀 The Hermes Learning Loop

How the system gets smarter over time:

Feedback: If a Property Manager manually corrects a fact in the .md, the engine triggers a Self-Correction Event.

User Modeling: It learns which facts the manager prioritizes (e.g., "Always keep the keybox code at the top") and updates its synthesis rules in system_prompts/style.md.

🛠️ Stack Suggestion

Core: Python / FastAPI

LLM: gemini-2.5-flash (for fast, high-context extraction) or Hermes-3-Llama-3.1 (for agentic reasoning).

Parsing: marko or mistune for Markdown AST manipulation.

Database: SQLite (FTS5) for indexing the source documents for provenance lookups.

🎯 Hackathon Goals

MVP: A script that takes 1 PDF and 1 Email and produces a merged property.md.

Stretch: Demonstrate the "Surgical Update" where a human edit is preserved while the AI updates a technical fact elsewhere in the doc.

Vision: A dashboard showing the "Confidence Score" of the building's current context state.