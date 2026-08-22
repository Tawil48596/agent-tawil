# Domain docs

This repository uses a single domain context.

## Before exploring

- Read root `CONTEXT.md` when it exists.
- Read ADRs under `docs/adr/` that affect the area being changed.
- Proceed silently when either path does not exist. Domain-modeling creates these files only after terminology or a durable decision is resolved.

## Vocabulary

Use canonical terms from `CONTEXT.md` in issue titles, specifications, tests, and code. Surface conflicts with that glossary instead of introducing synonyms. Record implementation-free definitions in `CONTEXT.md` as they are resolved.

## Decisions

Flag any proposal that contradicts an existing ADR. Create an ADR only when the decision is hard to reverse, surprising without context, and the result of a genuine trade-off.
