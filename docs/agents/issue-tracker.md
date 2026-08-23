# Issue tracker: GitHub

Issues and specifications for this repository live in GitHub Issues. Run `gh` commands from this clone so the remote selects the repository.

## Operations

- Create: `gh issue create --title "..." --body "..."`
- Read: `gh issue view <number> --comments`
- List: `gh issue list --state open --json number,title,body,labels,comments`
- Comment: `gh issue comment <number> --body "..."`
- Label: `gh issue edit <number> --add-label "..."` or `--remove-label "..."`
- Close: `gh issue close <number> --comment "..."`

When a skill says to publish a specification or ticket, create a GitHub issue. When it asks for a relevant ticket, read the issue and its comments.

## Pull requests as a triage surface

PRs as a request surface: no. Pull requests follow the repository review workflow and do not enter the issue triage queue.

GitHub shares issue and PR numbers. Resolve an ambiguous `#<number>` with `gh pr view <number>` and fall back to `gh issue view <number>`.

## Wayfinding

- Store a wayfinding map in one issue labelled `wayfinder:map`.
- Link child tickets with GitHub sub-issues when available; otherwise use a task list and `Part of #<map>`.
- Represent blockers with native issue dependencies when available; otherwise place `Blocked by: #<number>` at the top of the child issue.
- Claim work with `gh issue edit <number> --add-assignee @me` only when execution begins.
