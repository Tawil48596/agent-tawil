"""提示词/模型 A/B 对比"""


class ABCompare:
    """A/B 对比评测"""

    def compare(self, baseline: dict, candidate: dict) -> dict:
        b_pass = baseline.get("pass_rate", 0)
        c_pass = candidate.get("pass_rate", 0)
        b_score = baseline.get("avg_score", 0)
        c_score = candidate.get("avg_score", 0)

        return {
            "baseline": {"pass_rate": round(b_pass, 3), "avg_score": round(b_score, 3)},
            "candidate": {"pass_rate": round(c_pass, 3), "avg_score": round(c_score, 3)},
            "diff_pass_rate": round(c_pass - b_pass, 3),
            "diff_avg_score": round(c_score - b_score, 3),
            "winner": "candidate" if c_pass > b_pass and c_score > b_score else "baseline" if b_pass > c_pass else "tie",
        }

    def compare_multiple(self, results: dict[str, dict]) -> dict:
        """多组对比 {name: result, ...}"""
        rankings = sorted(results.items(), key=lambda x: x[1].get("pass_rate", 0), reverse=True)
        return {
            "rankings": [{"name": n, "pass_rate": r.get("pass_rate", 0), "avg_score": r.get("avg_score", 0)} for n, r in rankings],
            "best": rankings[0][0] if rankings else "",
        }
