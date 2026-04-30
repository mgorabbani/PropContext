# PropContext

**Every building gets a memory that heals itself.**

Property management is context work: every email, invoice, bank transaction,
owner question, contractor update, and meeting decision only makes sense when
you know the building behind it. Today that knowledge is scattered across
inboxes, PDFs, ERPs, bank exports, drives, and the memory of the property
manager who has been there for years.

PropContext turns that chaos into one living building memory per property: a clear,
source-backed knowledge file that people can inspect and AI agents can use
immediately.

https://www.loom.com/share/39c4214527ed4dd5a4bfc712ab65483a 
**[▶️ Watch Demo Video](https://www.loom.com/share/39c4214527ed4dd5a4bfc712ab65483a)** - Click to open in Loom

## The Pitch

PropContext is a self-healing context layer for property management AI.

Instead of making an agent crawl every document again and again, PropContext
compresses the important facts into a dense, readable property wiki. Each
building gets an always-current memory of owners, tenants, contractors, open
issues, invoices, decisions, obligations, and source references.

The inspiration is Karpathy's `llm-wiki` idea: a small, maintained markdown
knowledge base can be more useful and efficient than repeatedly searching a
large pile of raw documents. One compact building memory beats expensive RAG
gymnastics, chunk drift, and repeated context reconstruction.

## The Self-Healing Idea

PropContext does not regenerate the whole memory whenever something changes. It
classifies new information, finds the exact place it belongs, patches only that
section, preserves human notes, and keeps provenance back to the original
source.

Hermes is the self-improvement loop behind the engine: it watches where
ingestion misses facts, where schema gaps appear, and where agents need better
context. From that feedback, Hermes can propose updates to extraction rules,
wiki structure, vocabulary, and ingestion behavior so the system gets better
dynamically instead of staying frozen after deployment.

## Why It Matters

AI agents for property management do not fail because they lack reasoning. They
fail because they lack the right building context at the right time.

PropContext gives agents that context in the most efficient shape: one maintained,
auditable memory per property. The human reads it, the agent acts from it, git
remembers every change, and the ingestion engine keeps learning how to maintain
it better.
