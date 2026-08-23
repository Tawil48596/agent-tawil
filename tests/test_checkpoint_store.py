import os
import time

import pytest

from plugins.checkpoint.checkpoint_store import Checkpoint, CheckpointStore


def _store(tmp_path):
    return CheckpointStore({"checkpoint": {"path": str(tmp_path)}})


@pytest.mark.asyncio
async def test_checkpoint_save_is_atomic_and_updates_memory_after_commit(tmp_path, monkeypatch):
    store = _store(tmp_path)
    checkpoint = Checkpoint(id="cp-1", task_id="task-1", state={"step": 1})

    def fail_replace(_source, _destination):
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", fail_replace)
    with pytest.raises(OSError, match="disk full"):
        await store.save(checkpoint)

    task_dir = tmp_path / "task-1"
    assert not (task_dir / "cp-1.json").exists()
    assert list(task_dir.glob("*.tmp")) == []
    assert await store.load_latest("task-1") is None


@pytest.mark.asyncio
async def test_load_latest_falls_back_from_corrupt_checkpoint(tmp_path):
    store = _store(tmp_path)
    valid = Checkpoint(id="cp-valid", task_id="task-1", stage="working", state={"step": 1})
    await store.save(valid)

    corrupt = tmp_path / "task-1" / "cp-corrupt.json"
    corrupt.write_text("{incomplete", encoding="utf-8")
    future = time.time() + 10
    os.utime(corrupt, (future, future))

    restored = await _store(tmp_path).load_latest("task-1")

    assert restored is not None
    assert restored.id == "cp-valid"
    assert restored.state == {"step": 1}
