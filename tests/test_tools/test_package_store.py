import hashlib
import hmac
import io
import zipfile

import pytest

from plugins.tool_market.package_store import PackageManifest, ToolPackageStore


def package(files):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return stream.getvalue()


def signed_manifest(data, version, key="secret"):
    digest = hashlib.sha256(data).hexdigest()
    signature = hmac.new(key.encode(), digest.encode(), hashlib.sha256).hexdigest()
    return PackageManifest("demo", version, digest, signature)


def test_verified_install_persistence_and_rollback(tmp_path):
    store = ToolPackageStore(tmp_path, "secret")
    first = package({"tool.py": "VERSION = 1"})
    second = package({"tool.py": "VERSION = 2"})
    store.install(first, signed_manifest(first, "1.0.0"))
    store.install(second, signed_manifest(second, "2.0.0"))
    assert ToolPackageStore(tmp_path, "secret").status("demo")["active"] == "2.0.0"
    assert store.rollback("demo")["version"] == "1.0.0"


def test_rejects_tampering_and_path_traversal(tmp_path):
    store = ToolPackageStore(tmp_path, "secret")
    data = package({"tool.py": "safe"})
    with pytest.raises(ValueError, match="checksum"):
        store.install(data + b"tampered", signed_manifest(data, "1.0.0"))
    unsafe = package({"../escape.py": "bad"})
    with pytest.raises(ValueError, match="unsafe"):
        store.install(unsafe, signed_manifest(unsafe, "1.0.0"))
