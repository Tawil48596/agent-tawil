# Release checklist

1. Confirm `git status` is clean and inspect every committed path.
2. Run `python -m pytest` and require all tests to pass.
3. Run `npm ci` when dependencies change, then `npm run build`.
4. Run `git diff --check` and scan tracked files for API keys and tokens.
5. Verify Python, web, FastAPI and runtime versions are identical.
6. Start in development mode and check `/health`, `/ready`, `/metrics` and the Web UI.
7. Validate production configuration in a disposable environment without real credentials.
8. Push a release branch, open a Pull Request, wait for CI, review the diff, then merge.
9. Tag only the reviewed merge commit and publish release notes from `CHANGELOG.md`.
10. Retain the previous deployment and persistent-data backup for rollback.
