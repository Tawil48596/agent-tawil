# ADR 0003: Fail closed when tool side effects are uncertain

- Status: Accepted
- Date: 2026-08-23

## Context

A process can stop after an external tool produces a side effect but before its result is safely
returned. Blind retry would risk duplicate files, messages, purchases, or remote mutations.

## Decision

Each recoverable Tool Call is keyed by Session ID and stable call ID. The Execution Ledger records
a lease before execution and atomically stores successful results. A restart replays completed
results without invoking the tool. An active lease waits; an expired, corrupt, or ambiguous record
becomes an Uncertain Execution that requires explicit human reconciliation before retry.
Checkpoints restore workflow state, while the ledger remains the authority for tool side effects.

## Consequences

Recovery favors safety over automatic progress. Operators may need to inspect the external system
before clearing an Uncertain Execution, but the runtime can prove why a call was replayed, blocked,
or executed.
