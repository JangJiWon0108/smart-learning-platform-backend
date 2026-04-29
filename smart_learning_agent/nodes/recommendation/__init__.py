"""
문제 추천 라우트 노드 공개 API.
"""

from .curator_output_nodes import build_curator_output_func

__all__ = [
    "build_curator_output_func",
]
