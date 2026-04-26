**Criteria for a strong solution**

- generalize beyond the provided dataset and data format
- resolve easy information conflicts automatically and involve humans where ambiguity actually matters
- preserve provenance at the fact level and update automatically when source facts change

This is not a challenge about dumping markdown into folders or building a documentation chatbot. It is about designing a context base that is explainable, editable, robust under change, and useful in practice. Involve humans when it matters, and take over their work as much as possible where it does not.

**Other Product Thoughts**

- cover both graph construction and retrieval
- treat the virtual file system as a product surface, not just storage
- optimize for long-term maintainability by humans and machines

**Your Goal**

Build an engine that produces a single Context Markdown File per property. That's a living, self-updating document containing every fact an AI agent needs to act. Dense, structured, traced to its source, surgically updated without destroying human edits. Think CLAUDE.md, but for a building, plus it writes itself.

**Why this is hard**

1. Schema alignment: "owner" is called Eigentümer, MietEig, Kontakt, or owner depending on the source system. You must resolve identities across ERPs.

2. Surgical updates: when an new email arrives you can't generate a whole new file. Regenerating the file destroys human edits and burns tokens. You must patch exactly the right section.

3. Signal vs. noise: 90% of emails are irrelevant. The engine must judge what belongs in the context and what doesn't.
