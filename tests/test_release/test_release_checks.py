import subprocess

from shared.release_checks import scan_text, scan_tracked_files


def test_secret_scan_identifies_kind_without_returning_value():
    secret = "sk-" + "A" * 24

    findings = scan_text(f"safe\nkey={secret}")

    assert findings == [(2, "openai_key")]
    assert secret not in repr(findings)


def test_secret_scan_ignores_placeholders():
    assert scan_text("OPENAI_API_KEY=your-key-here\nghp_example") == []


def test_secret_scan_ignores_tracked_files_deleted_from_worktree(tmp_path):
    repository = tmp_path / "repository"
    repository.mkdir()
    subprocess.run(["git", "init"], cwd=repository, check=True, capture_output=True)
    stale_asset = repository / "old-build.js"
    stale_asset.write_text("const build = 'old';", encoding="utf-8")
    subprocess.run(
        ["git", "add", "old-build.js"],
        cwd=repository,
        check=True,
        capture_output=True,
    )
    stale_asset.unlink()

    assert scan_tracked_files(repository) == []


def test_secret_scan_includes_untracked_nonignored_files(tmp_path):
    repository = tmp_path / "repository"
    repository.mkdir()
    subprocess.run(["git", "init"], cwd=repository, check=True, capture_output=True)
    candidate = repository / "new-config.txt"
    candidate.write_text("token=" + "sk-" + "A" * 24, encoding="utf-8")

    assert scan_tracked_files(repository) == [
        {"path": "new-config.txt", "line": 1, "kind": "openai_key"}
    ]
