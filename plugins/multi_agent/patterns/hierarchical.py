"""层级协作: 主编排器 → 子编排器 → Worker"""

from collections.abc import Callable


class HierarchicalPattern:
    """层级编排模式"""

    async def execute(self, plan: dict, executor: Callable, sub_executor: Callable = None) -> dict:
        """plan = {teams: [{name, tasks: [...]}, ...]}"""
        team_results = []
        for team in plan.get("teams", []):
            team_output = {"team": team.get("name", ""), "tasks": []}
            if sub_executor:
                for task in team.get("tasks", []):
                    result = await sub_executor(task)
                    team_output["tasks"].append(result)
            team_results.append(team_output)

        if executor:
            summary = await executor({"goal": "总结以下团队结果:\n" + str(team_results)})
            return {"teams": team_results, "summary": summary.get("result", "")}

        return {"teams": team_results}
