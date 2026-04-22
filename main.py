"""
backend 로컬 실행 진입점.

사용:
  uv run python main.py "포인터 관련 문제 1개만 추천해줘"
"""

import asyncio
import sys

from google.adk.artifacts import InMemoryArtifactService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from smart_learning_agent.agent import root_agent

_artifact_service = InMemoryArtifactService()
_session_service = InMemorySessionService()


async def run_query(query: str) -> None:
    runner = Runner(
        agent=root_agent,
        app_name=root_agent.name,
        artifact_service=_artifact_service,
        session_service=_session_service,
    )
    session = await _session_service.create_session(
        app_name=runner.app_name,
        user_id="test_user",
    )

    content = types.Content(role="user", parts=[types.Part(text=query)])

    last_text: str | None = None
    async for event in runner.run_async(
        user_id="test_user",
        session_id=session.id,
        new_message=content,
    ):
        if event.is_final_response() and event.content:
            for part in event.content.parts:
                if part.text:
                    last_text = part.text

    if last_text:
        print(last_text)


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]).strip() or "포인터 관련 문제 1개만 추천해줘"
    asyncio.run(run_query(q))
