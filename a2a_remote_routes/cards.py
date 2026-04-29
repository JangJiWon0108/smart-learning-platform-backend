"""
A2A discovery용 AgentCard 구성 모듈.

책임
- route별 설명 문자열 관리
- `AgentCard` / `AgentSkill` 구성
"""

from __future__ import annotations

from typing import Any

from a2a.types import AgentCapabilities, AgentCard, AgentSkill

ROUTE_DESCRIPTIONS: dict[str, str] = {
    "solver": "정보처리기사 실기 문제 풀이와 개념 설명 route",
    "recommendation": "정보처리기사 실기 유사 문제 추천 route",
    "visualization": "코드 실행 흐름 시각화 route",
    "other": "지원 범위 밖 질문 안내 route",
}


def build_agent_card(route: str, host: str, port: int, agent: Any) -> AgentCard:
    """
    A2A discovery용 AgentCard 구성.

    초보 독자를 위한 포인트:
    - AgentCard는 "이 서버가 어떤 에이전트인지"를 외부(discovery/RPC)에서 알기 위한 메타데이터입니다.
    - 여기서는 route별로 name/description/url/skills 정도만 채워 둡니다.
    """
    if route not in ROUTE_DESCRIPTIONS:
        raise ValueError(
            f"Unknown route={route!r}. expected one of {sorted(ROUTE_DESCRIPTIONS)}"
        )
    rpc_url = f"http://{host}:{port}/" if port else f"http://{host}/"
    return AgentCard(
        name=agent.name,
        description=ROUTE_DESCRIPTIONS[route],
        url=rpc_url,
        version="0.1.0",
        capabilities=AgentCapabilities(streaming=True),
        defaultInputModes=["text/plain"],
        defaultOutputModes=["text/plain", "application/json"],
        skills=[
            AgentSkill(
                id=f"{route}_route",
                name=f"{route} route",
                description=ROUTE_DESCRIPTIONS[route],
                tags=["smart-learning", route],
            )
        ],
    )

