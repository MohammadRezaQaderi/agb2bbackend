from __future__ import annotations

from typing import Any


def build_comment_list_response(comments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": comment.get("id"),
            "name": comment.get("name"),
            "comment": comment.get("comment"),
            "rating": comment.get("rating"),
            "persian_date": comment.get("persian_date"),
        }
        for comment in comments
    ]
