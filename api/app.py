"""
FastAPI 서버 진입점.

사용:
  uv run uvicorn api.app:app --reload --app-dir .
"""

import json
import re
import time
import uuid
from typing import Any, AsyncGenerator

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import InMemoryRunner
from google.genai import types

from nodes.image_nodes import IMAGE_ARTIFACT_KEY
from smart_learning_agent.agent import root_agent

_workflow_runner = InMemoryRunner(
    node=root_agent,
    app_name=root_agent.name,
)

app = FastAPI(title="Smart Learning Platform API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


def _normalize_tracer_output_with_original_code(
    tracer_data: Any,
    tracer_code: str | None,
) -> Any:
    """
    TracerOutput.original_code는 "사용자 입력 원문 코드"와 1:1로 동일해야 한다.
    LLM이 시각화 편의상 예시 코드를 재작성하는 경우가 있어, API 응답 직전에 원문으로 정규화한다.
    """
    if not tracer_code or not isinstance(tracer_code, str):
        return tracer_data

    if hasattr(tracer_data, "model_dump"):
        tracer_data = tracer_data.model_dump()
    if not isinstance(tracer_data, dict):
        return tracer_data

    code_lines = tracer_code.splitlines()

    tracer_data["original_code"] = tracer_code

    steps = tracer_data.get("steps")
    if isinstance(steps, list):
        for s in steps:
            if not isinstance(s, dict):
                continue
            line = s.get("line")
            if not isinstance(line, int) or line <= 0:
                continue
            if line <= len(code_lines):
                s["code"] = code_lines[line - 1].rstrip("\n")

    return tracer_data




def _extract_question_number(problem: dict[str, Any]) -> int | None:
    qn = problem.get("question_number")
    if isinstance(qn, int):
        return qn
    q = str(problem.get("question") or "")
    m = re.search(r"(?:\[문제\]\s*)?(\d{1,2})\s*\.", q)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            return None
    return None


def _accent_for(problem: dict[str, Any]) -> str:
    diff = str(problem.get("difficulty") or "").lower()
    if diff == "hard":
        return "rose"
    if diff == "easy":
        return "cyan"
    return "violet"


def _match_label_for(problem: dict[str, Any]) -> str:
    subj = str(problem.get("subject") or "").strip()
    return subj or "추천"


def _build_refine_lookup(refine_output: Any) -> dict[str, Any]:
    """refine_output 상태값에서 {id: RefinedProblem dict} 룩업 테이블을 생성한다."""
    if refine_output is None:
        return {}
    if hasattr(refine_output, "model_dump"):
        refine_output = refine_output.model_dump()
    if not isinstance(refine_output, dict):
        return {}
    lookup: dict[str, Any] = {}
    for rp in refine_output.get("refined_problems") or []:
        if isinstance(rp, dict) and rp.get("id"):
            lookup[rp["id"]] = rp
    return lookup


def _to_problem_cards(
    curator_output: dict[str, Any],
    refine_lookup: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    problems = (curator_output.get("recommended_problems") or [])[:3]
    if not isinstance(problems, list):
        return []
    refine_lookup = refine_lookup or {}
    cards: list[dict[str, Any]] = []
    for p in problems:
        if not isinstance(p, dict):
            continue
        year = int(p.get("year") or 0)
        rnd = int(p.get("round") or 0)
        qn = _extract_question_number(p) or 0
        q_text = str(p.get("question") or "").strip()
        problem_id = str(p.get("id") or "")

        refined = refine_lookup.get(problem_id)
        stem = (refined.get("refined_question") or q_text) if refined else q_text
        code = (refined.get("refined_code") or None) if refined else None
        code_language = (refined.get("code_language") or None) if refined else None

        cards.append(
            {
                "problemId": problem_id,
                "year": year,
                "round": rnd,
                "questionNumber": qn,
                "examTitle": f"[{year}년 {rnd}회] 정보처리기사 실기",
                "stemPreview": stem,
                "officialAnswer": str(p.get("answer") or "") or None,
                "matchLabel": _match_label_for(p),
                "accent": _accent_for(p),
                "subject": p.get("subject"),
                "difficulty": p.get("difficulty"),
                "similarityScore": p.get("similarity_score"),
                "question": stem,
                "code": code,
                "codeLanguage": code_language,
                "answer": p.get("answer"),
                "explanation": p.get("explanation"),
            }
        )
    return cards


@app.post("/chat")
async def chat(
    query: str = Form(default=""),
    image: UploadFile | None = File(default=None),
):
    """텍스트 질문 또는 이미지(정보처리기사 실기 문제)를 처리한다."""
    if not query.strip() and image is None:
        raise HTTPException(status_code=400, detail="query 또는 image 중 하나는 필수입니다.")

    user_id = "api_user"
    session_id = str(uuid.uuid4())

    await _workflow_runner.session_service.create_session(
        app_name=_workflow_runner.app_name,
        user_id=user_id,
        session_id=session_id,
    )

    parts: list[types.Part] = []
    if query.strip():
        parts.append(types.Part(text=query.strip()))

    if image is not None:
        mime_type = image.content_type or "image/jpeg"
        if mime_type not in _ALLOWED_MIME_TYPES:
            raise HTTPException(status_code=415, detail=f"지원하지 않는 이미지 형식입니다: {mime_type}")

        image_bytes = await image.read()

        artifact = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        await _workflow_runner.artifact_service.save_artifact(
            app_name=_workflow_runner.app_name,
            user_id=user_id,
            session_id=session_id,
            filename=IMAGE_ARTIFACT_KEY,
            artifact=artifact,
        )

        parts.append(types.Part(inline_data=types.Blob(data=image_bytes, mime_type=mime_type)))

    if not parts:
        parts.append(types.Part(text=""))

    content = types.Content(role="user", parts=parts)

    response_text: str | None = None
    async for event in _workflow_runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=content,
    ):
        if event.is_final_response() and event.content:
            for part in event.content.parts:
                if part.text:
                    response_text = part.text

    session = await _workflow_runner.session_service.get_session(
        app_name=_workflow_runner.app_name,
        user_id=user_id,
        session_id=session_id,
    )
    state = session.state or {} if session else {}
    current_route = state.get("current_route")

    if "curator_output" in state:
        curator_data = state["curator_output"]
        if hasattr(curator_data, "model_dump"):
            curator_data = curator_data.model_dump()
        if isinstance(curator_data, dict):
            refine_lookup = _build_refine_lookup(state.get("refine_output"))
            cards = _to_problem_cards(curator_data, refine_lookup)
            message = None
            if not cards:
                message = (
                    "지금 조건에 맞는 추천 문제가 없어요.\n\n"
                    "- 검색 범위를 넓혀서 다시 요청해보세요 (예: “최근 3개”, “난이도 상관없이”).\n"
                    "- 과목/유형을 조금 바꿔보세요 (예: C 포인터 → 구조체 포인터/이중 포인터).\n"
                    "- 원하시면 제가 비슷한 유형으로 1~3개를 직접 구성해드릴게요."
                )
            return {
                "type": "curation",
                "route": current_route,
                "title": "맞춤 추천 문제 카드",
                "problemCards": cards,
                "message": message,
                "raw": curator_data,
            }

    if "tracer_output" in state:
        tracer_data = state["tracer_output"]
        tracer_data = _normalize_tracer_output_with_original_code(tracer_data, state.get("tracer_code"))
        return {"type": "tracer", "route": current_route, "data": tracer_data}

    return {"type": "text", "route": current_route, "response": response_text or "응답을 생성하지 못했습니다."}


@app.post("/chat/stream")
async def chat_stream(
    query: str = Form(default=""),
    image: UploadFile | None = File(default=None),
):
    """SSE 스트리밍 응답. tracer 라우트는 마지막에 JSON 이벤트로 전송."""
    if not query.strip() and image is None:
        raise HTTPException(status_code=400, detail="query 또는 image 중 하나는 필수입니다.")

    user_id = "api_user"
    session_id = str(uuid.uuid4())

    await _workflow_runner.session_service.create_session(
        app_name=_workflow_runner.app_name,
        user_id=user_id,
        session_id=session_id,
    )

    parts: list[types.Part] = []
    if query.strip():
        parts.append(types.Part(text=query.strip()))

    if image is not None:
        mime_type = image.content_type or "image/jpeg"
        if mime_type not in _ALLOWED_MIME_TYPES:
            raise HTTPException(status_code=415, detail=f"지원하지 않는 이미지 형식입니다: {mime_type}")
        image_bytes = await image.read()
        artifact = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        await _workflow_runner.artifact_service.save_artifact(
            app_name=_workflow_runner.app_name,
            user_id=user_id,
            session_id=session_id,
            filename=IMAGE_ARTIFACT_KEY,
            artifact=artifact,
        )
        parts.append(types.Part(inline_data=types.Blob(data=image_bytes, mime_type=mime_type)))

    if not parts:
        parts.append(types.Part(text=""))

    content = types.Content(role="user", parts=parts)

    async def event_generator() -> AsyncGenerator[str, None]:
        # curator_agent는 JSON 텍스트를 생성하므로 스트리밍 청크에서 제외하고,
        # 종료 시 state의 curator_output을 'curation' 데이터 이벤트로 전송한다.
        _STREAM_NODES = {"solver_agent", "curator_intro_agent", "tracer_intro_agent", "fallback_agent"}
        _emitted_nodes: set[str] = set()

        async for event in _workflow_runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=content,
            run_config=RunConfig(streaming_mode=StreamingMode.SSE),
        ):
            node_info = getattr(event, "node_info", None)
            node_name = getattr(node_info, "name", None) if node_info else None

            if node_name and node_name not in _emitted_nodes:
                _emitted_nodes.add(node_name)
                yield f"data: {json.dumps({'type': 'state', 'node': node_name})}\n\n"

            if not event.partial or not event.content:
                continue
            if node_name not in _STREAM_NODES:
                continue
            for part in event.content.parts:
                if part.text and not getattr(part, "function_call", None):
                    yield f"data: {json.dumps({'type': 'chunk', 'text': part.text})}\n\n"

        session = await _workflow_runner.session_service.get_session(
            app_name=_workflow_runner.app_name,
            user_id=user_id,
            session_id=session_id,
        )
        state = session.state or {} if session else {}

        if "curator_output" in state:
            curator_data = state["curator_output"]
            if hasattr(curator_data, "model_dump"):
                curator_data = curator_data.model_dump()
            if isinstance(curator_data, dict):
                refine_lookup = _build_refine_lookup(state.get("refine_output"))
                cards = _to_problem_cards(curator_data, refine_lookup)
                message = None
                if not cards:
                    message = (
                        "지금 조건에 맞는 추천 문제가 없어요.\n\n"
                        "- 검색 범위를 넓혀서 다시 요청해보세요 (예: “최근 3개”, “난이도 상관없이”).\n"
                        "- 과목/유형을 조금 바꿔보세요 (예: C 포인터 → 구조체 포인터/이중 포인터).\n"
                        "- 원하시면 제가 비슷한 유형으로 1~3개를 직접 구성해드릴게요."
                    )
                payload = {
                    "type": "curation",
                    "route": state.get("current_route"),
                    "title": "맞춤 추천 문제 카드",
                    "problemCards": cards,
                    "message": message,
                    "raw": curator_data,
                }
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

        if "tracer_output" in state:
            tracer_data = state["tracer_output"]
            tracer_data = _normalize_tracer_output_with_original_code(tracer_data, state.get("tracer_code"))
            yield f"data: {json.dumps({'type': 'tracer', 'route': state.get('current_route'), 'data': tracer_data}, ensure_ascii=False)}\n\n"

        yield f"data: {json.dumps({'type': 'done', 'route': state.get('current_route')})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/health")
async def health():
    return {"status": "ok"}
