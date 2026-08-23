# ADR 0004: Layer approval, policy, and execution isolation

- Status: Accepted
- Date: 2026-08-23

## Context

Tool risk cannot be controlled by a prompt alone. File and command tools may modify local state,
expose environment data, or access the network.

## Decision

Tool execution uses three independent controls: policy classifies and rejects commands, protected
tools require a time-bounded Approval Request, and executable work runs with an allowlisted
environment plus timeout and resource controls. Docker mode additionally defaults to no network
and a read-only root; subprocess mode is a development fallback and is not described as a hard
security boundary.

## Consequences

The runtime can explain whether a request was blocked, awaiting approval, timed out, or executed.
Docker remains required when hostile code isolation is part of the threat model, and deployments
must explicitly opt into network access.
