# ADR 0002: Discover explicit plugin entrypoints around composed state

- Status: Accepted
- Date: 2026-08-23

## Context

Plugin classes existed but were neither registered nor started, and several classes would create
duplicate model, security, or observability state if activated directly.

## Decision

A plugin opts in with a `plugin.py` module exposing `create_plugin()`. The manager discovers these
entrypoints, resolves dependencies, loads and enables them, and disables them in reverse order.
The composition root creates each state owner once and publishes it through the dependency
container; plugins expose those same instances as namespaced extensions. A failed plugin is
reported as `error`, its dependants become `blocked`, and independent plugins continue.

## Consequences

Adding a conforming plugin does not require editing the composition root, health output reflects
real lifecycle state, and duplicate runtime owners are avoided. Missing or circular dependencies
remain startup contract errors because no safe ordering exists.
