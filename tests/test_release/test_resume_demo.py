import pytest

from scripts.run_resume_demo import run


@pytest.mark.asyncio
async def test_resume_demo_produces_machine_readable_evidence(tmp_path):
    output = tmp_path / "resume-demo.json"

    report = await run(output)

    assert report["passed"] is True
    assert report["execution_count"] == 2
    assert report["checks"]["restart_replayed_result"] is True
    assert report["checks"]["uncertain_execution_blocked"] is True
    assert report["checks"]["hitl_reconciled"] is True
    assert report["trace"]["span_count"] == 6
    assert report["trace"]["has_error"] is True
    assert report["eval"]["pass_rate"] == 1.0
    assert output.exists()
