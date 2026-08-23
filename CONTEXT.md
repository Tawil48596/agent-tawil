# Domain context

## Purpose

This repository implements a local-first Agent Runtime that can execute model-selected tools,
survive interrupted work, require human decisions for risky or uncertain actions, and produce
auditable evidence for evaluation.

## Canonical language

- **Agent Runtime** — The boundary that coordinates a model, conversation state, tools,
  approvals, recovery, and observability for one running application.
- **Session** — A durable conversation identity and its ordered messages, independent of any
  single browser connection or model request.
- **Tool Call** — A model-requested operation identified within a Session by a stable call ID,
  tool name, and arguments.
- **Approval Request** — A time-bounded human decision that must resolve before a protected Tool
  Call may execute.
- **Execution Ledger** — The durable record used to decide whether a Tool Call should execute,
  replay a completed result, wait, or stop for reconciliation.
- **Uncertain Execution** — A Tool Call whose external side effect cannot be proven absent or
  complete after interruption. It must not be retried automatically.
- **Checkpoint** — A durable snapshot from which unfinished agent work can resume.
- **Trace** — A redacted, correlated account of one runtime operation and its child operations,
  including timing and token usage.
- **Plugin** — An explicitly discoverable lifecycle participant that exposes extensions while
  using the Agent Runtime's existing state owners.
- **Evaluation** — A repeatable measurement of behavior, tool selection, arguments, token use,
  and latency against declared expectations.

## Invariants

- A completed Tool Call is not executed twice for the same Session and call ID.
- An Uncertain Execution requires explicit reconciliation before retry.
- Protected tools do not run without an approved Approval Request.
- Secrets and raw sensitive payloads are excluded from persisted traces and release evidence.
- A Plugin never creates a second owner for a runtime component already composed by the Agent
  Runtime.
