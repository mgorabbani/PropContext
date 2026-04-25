# BerlinHackBuena

Context management project for a Berlin hackathon.

## Overview

BerlinHackBuena is an early-stage hackathon project focused on turning scattered business context into usable, searchable, and explainable information. The repository currently contains a sample data set under `hackathon/` with documents such as invoices, emails, letters, bank data, master data, and incremental updates.

The goal is to build a system that can ingest these sources, extract relevant facts, preserve provenance, and help users answer operational questions with the right context.

## Repository Structure

```text
.
├── hackathon/
│   ├── bank/          # Bank-related source data
│   ├── briefe/        # Letters and written correspondence
│   ├── emails/        # Email source files
│   ├── incremental/   # Incremental data drops or updates
│   ├── rechnungen/    # Invoice PDFs
│   └── stammdaten/    # Master data
└── README.md
```

## Project Goals

- Ingest structured and unstructured business documents.
- Extract entities, dates, amounts, relationships, and document metadata.
- Link information across emails, invoices, bank records, letters, and master data.
- Provide a context layer that supports reliable search, retrieval, and question answering.
- Keep source references available so answers can be traced back to original documents.

## Initial Ideas

- Document parsing pipeline for PDFs, emails, and tabular files.
- Normalized data model for contacts, companies, invoices, payments, messages, and events.
- Vector and keyword search over extracted content.
- Context API for retrieving the most relevant facts and source snippets.
- Simple user interface for exploring documents and asking questions.

## Getting Started

There is no application scaffold yet. A suggested next step is to choose the implementation stack and add the first runnable service.

Possible first milestones:

1. Add a document ingestion script.
2. Extract metadata from invoices and emails.
3. Store extracted records in a local database.
4. Add search over the extracted content.
5. Build a small UI or API for querying the context store.

## Data Notes

The `hackathon/` directory appears to contain hackathon data and should be treated as project input. Avoid committing generated indexes, embeddings, temporary parse outputs, or local databases unless the team explicitly decides they belong in version control.

## Development Notes

Add stack-specific setup instructions here once the project has a runtime, for example:

```bash
# install dependencies

# run tests

# start the app
```

## License

License not specified yet.
