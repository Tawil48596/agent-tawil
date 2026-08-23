import zipfile

import pytest

from shared.data_backup import create_backup, restore_backup, verify_backup


def test_backup_round_trip_and_manifest(tmp_path):
    source = tmp_path / "source"
    (source / "traces").mkdir(parents=True)
    (source / "traces" / "history.json").write_text("trace", encoding="utf-8")
    archive = tmp_path / "backup.zip"

    manifest = create_backup(source, archive)
    verified = verify_backup(archive)
    restore_backup(archive, tmp_path / "restored")

    assert manifest["schema_version"] == 1
    assert verified["files"][0]["path"] == "data/traces/history.json"
    assert (tmp_path / "restored/traces/history.json").read_text(encoding="utf-8") == "trace"


def test_backup_rejects_path_traversal(tmp_path):
    archive = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("data/../secret", b"x")
        bundle.writestr(
            "manifest.json",
            '{"schema_version":1,"files":[{"path":"data/../secret",'
            '"size":1,"sha256":"'
            '2d711642b726b04401627ca9fbac32f5c8530fb1903cc4db02258717921a4881"}]}',
        )

    with pytest.raises(ValueError, match="Unsafe backup member"):
        verify_backup(archive)
