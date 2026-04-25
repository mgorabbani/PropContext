Property management runs on context. Every ticket, email, and owner question requires knowing a hundred things about one specific building: Who owns it, what the last assembly decided, whether the roof leak is open, who the heating contractor is.

Today, that context is scattered across ERPs, Gmail, Slack, Google Drive, scanned PDFs, and the head of the property manager who's been there twelve years. AI agents have to crawl all of it for every single task.

**Your Goal**

Build an engine that produces a single Context Markdown File per property. That's a living, self-updating document containing every fact an AI agent needs to act. Dense, structured, traced to its source, surgically updated without destroying human edits. Think CLAUDE.md, but for a building, plus it writes itself.

**Why this is hard**

1. Schema alignment: "owner" is called Eigentümer, MietEig, Kontakt, or owner depending on the source system. You must resolve identities across ERPs.

2. Surgical updates: when an new email arrives you can't generate a whole new file. Regenerating the file destroys human edits and burns tokens. You must patch exactly the right section.

3. Signal vs. noise: 90% of emails are irrelevant. The engine must judge what belongs in the context and what doesn't.
