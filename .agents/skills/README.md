# Project-owned engineering skills

This directory vendors the promoted `engineering/` and `productivity/` skills from [mattpocock/skills](https://github.com/mattpocock/skills).

- Upstream commit: `5b15a47f2d7150f545fbcacbfe381787fc0230dc`
- Included: 25 promoted skills and their directly referenced support files
- Excluded: upstream `misc/`, `in-progress/`, and `deprecated/` buckets
- License: see `LICENSE`

The repository copy is the source used by project agents. A developer may also install the same snapshot globally, but global files are never committed from the home directory.

## Updating

1. Review the new upstream commit and promoted-skill list.
2. Reinstall the selected skill directories with Codex `skill-installer` into `.agents/skills/`.
3. Update the pinned commit and license when upstream changes them.
4. Verify every skill has `SKILL.md`, scan the imported text for credentials, and run the project release gates before committing.
