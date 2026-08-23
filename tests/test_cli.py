from cli import AgentCLI
from shared.version import APP_VERSION


def test_cli_uses_the_dispatcher_that_owns_builtin_tools():
    cli = AgentCLI()

    assert cli.engine.tool_dispatcher is cli.tool_dispatcher
    assert cli.tool_dispatcher.list_tools() == ["echo", "get_current_time"]
    assert APP_VERSION in cli.intro
