"""工具评分 & 评论"""

import time
from dataclasses import dataclass, field


@dataclass
class Review:
    user: str = ""
    rating: int = 5
    comment: str = ""
    created_at: float = field(default_factory=time.time)


class RatingSystem:
    """工具评分系统"""

    def __init__(self):
        self._ratings: dict[str, list[int]] = {}
        self._reviews: dict[str, list[Review]] = {}

    def rate(self, tool_name: str, score: int, user: str = "anonymous", comment: str = ""):
        if score < 1 or score > 5:
            raise ValueError("Score must be 1-5")
        self._ratings.setdefault(tool_name, []).append(score)
        if comment:
            self._reviews.setdefault(tool_name, []).append(
                Review(user=user, rating=score, comment=comment)
            )

    def get_rating(self, tool_name: str) -> dict:
        scores = self._ratings.get(tool_name, [])
        if not scores:
            return {"average": 0.0, "count": 0, "distribution": {}}
        dist = {i: scores.count(i) for i in range(1, 6)}
        return {
            "average": round(sum(scores) / len(scores), 1),
            "count": len(scores),
            "distribution": dist,
        }

    def get_reviews(self, tool_name: str, limit: int = 20) -> list[dict]:
        return [
            {"user": r.user, "rating": r.rating, "comment": r.comment, "created_at": r.created_at}
            for r in self._reviews.get(tool_name, [])[-limit:]
        ]

    def get_top_rated(self, min_reviews: int = 3, limit: int = 10) -> list[dict]:
        results = []
        for name in self._ratings:
            rating = self.get_rating(name)
            if rating["count"] >= min_reviews:
                results.append({"name": name, **rating})
        results.sort(key=lambda r: r["average"], reverse=True)
        return results[:limit]
