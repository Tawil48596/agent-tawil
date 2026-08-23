# Release checklist

首选入口：`python -m scripts.run_release_gates`。任一门禁失败或超过预算时返回非零退出码，机器证据默认写入 `data/release/evidence.json`。

1. Confirm `git status` is clean and inspect every committed path.
2. Run `python -m pytest` and require all tests to pass.
3. Run `npm ci` when dependencies change, then require `npm run lint`, `npm test` and `npm run build` to pass.
4. Run `git diff --check` and scan tracked files for API keys and tokens.
5. Verify Python, web, FastAPI and runtime versions are identical.
6. Start in development mode and check `/health`, `/ready`, `/metrics` and the Web UI.
7. Validate production configuration in a disposable environment without real credentials.
8. Push a release branch, open a Pull Request, wait for CI, review the diff, then merge.
9. Tag only the reviewed merge commit and publish release notes from `CHANGELOG.md`.
10. Retain the previous deployment and persistent-data backup for rollback.
