"""Test Execution Guard"""

from plugins.security.execution_guard import ExecutionGuard


def test_block_dangerous():
    eg = ExecutionGuard()
    decision = eg.check("rm -rf /home")
    assert not decision.allowed


def test_approval_needed():
    eg = ExecutionGuard()
    decision = eg.check("sudo systemctl restart nginx")
    assert decision.requires_approval


def test_safe_command():
    eg = ExecutionGuard()
    decision = eg.check("ls -la")
    assert decision.allowed and not decision.requires_approval
