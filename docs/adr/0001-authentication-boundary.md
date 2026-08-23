# ADR 0001: Keep authentication at the HTTP boundary

- Status: Accepted
- Date: 2026-08-23

## Context

The project is local-first but can expose state-changing APIs. Authentication must be optional
for local development without allowing a partially configured protected deployment to appear
usable.

## Decision

When authentication is enabled, one HTTP middleware protects every `/api/v1/` endpoint except
token issuance. Tokens are issued only when administrator credentials are configured outside the
repository, and API keys are shown once and stored only as salted hashes. Domain components do
not parse credentials.

## Consequences

The API boundary is easy to audit and test, while non-HTTP adapters must establish their own
identity before invoking domain behavior. The current in-memory API-key and revocation stores are
appropriate for local use, not a production identity service.
