from __future__ import annotations

from typing import Any, AsyncGenerator

from google.adk import Event
from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.parallel_agent import ParallelAgent

from config.gemini_retry import GEMINI_GENERATE_CONTENT_RETRY_CONFIG
from config.llm_factory import get_adk_model
from config.properties import Settings
from schemas.refine import RefineOutput, RefinedProblem

settings = Settings()


_SINGLE_PROBLEM_INSTRUCTION = """
당신은 정보처리기사 기출 문제 텍스트를 정제하는 전문가입니다.

입력 문제:
{problem_json}

위 입력 문제 1개를 정제하세요.

## 정제 규칙

### refined_question (문제 지문)
- [문제], [cs], [정답], [답], colored by, 정답], 답] 같은 아티팩트를 제거하세요.
- 코드/테이블 데이터는 refined_code로 분리하고 여기서는 제외하세요.
- 문제 번호(예: "6.") 이후의 순수 지문만 남기세요.
- 보기가 있으면(1) 2) 3) 형식) 그대로 유지하세요.

### refined_code (코드 / 테이블)
- 코드나 테이블이 없으면 null을 반환하세요.
- **SQL 테이블 데이터**: 파이프(`|`) 기반 마크다운 표로 변환하세요.
  예: `컬럼1 | 컬럼2\\n값1 | 값2` → 마크다운 표
- **SQL 쿼리**: 키워드 대문자, 각 절을 새 줄로 분리해 가독성을 높이세요.
- **Java / C 코드**: 중괄호 기반으로 4칸 들여쓰기를 적용하세요.
- **Python 코드**: 콜론/키워드(def, if, for, while, class 등) 기반으로 4칸 들여쓰기를 적용하세요.
- 원본 로직은 절대 변경하지 마세요.

### code_language
- Java 코드면 "java", C 코드면 "c", Python이면 "python", SQL이면 "sql"
- 코드/테이블이 없으면 null

## 출력 형식
- RefinedProblem JSON 1개만 출력하세요.
- id는 입력 문제의 id를 그대로 사용하세요.
- 순수 JSON만 출력하세요. 마크다운 코드블록(```)으로 감싸지 마세요.
""".strip()


class ParallelProblemRefineAgent(BaseAgent):
    """추천 문제(0~3개)를 문제별로 병렬 정제하고, refine_output으로 합친다."""

    def __init__(self) -> None:
        super().__init__(
            name="problem_refine_parallel_agent",
            description="추천 문제를 문제별로 병렬 정제(들여쓰기/포맷)하는 에이전트",
            sub_agents=[],
        )

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        curator_output: Any = (ctx.session.state or {}).get("curator_output")
        if hasattr(curator_output, "model_dump"):
            curator_output = curator_output.model_dump()

        problems: list[dict[str, Any]] = []
        if isinstance(curator_output, dict):
            raw = curator_output.get("recommended_problems") or []
            if isinstance(raw, list):
                problems = [p for p in raw if isinstance(p, dict)]

        problems = problems[:3]

        if not problems:
            empty: dict[str, Any] = RefineOutput(refined_problems=[]).model_dump()
            yield Event(state={"refine_output": empty})
            return

        refine_agents: list[LlmAgent] = []
        output_keys: list[str] = []
        for idx, p in enumerate(problems):
            output_key = f"refined_problem_{idx}"
            output_keys.append(output_key)
            refine_agents.append(
                LlmAgent(
                    name=f"problem_refine_item_{idx}",
                    model=get_adk_model(settings, purpose="curator"),
                    generate_content_config=GEMINI_GENERATE_CONTENT_RETRY_CONFIG,
                    output_schema=RefinedProblem,
                    output_key=output_key,
                    description="단일 추천 문제 정제",
                    instruction=_SINGLE_PROBLEM_INSTRUCTION.format(problem_json=p),
                )
            )

        parallel = ParallelAgent(
            name="problem_refine_parallel_fanout",
            sub_agents=refine_agents,
            description="추천 문제별 정제를 병렬 실행",
        )

        async for event in parallel.run_async(ctx):
            yield event

        refined: list[dict[str, Any]] = []
        for idx, key in enumerate(output_keys):
            item = (ctx.session.state or {}).get(key)
            if hasattr(item, "model_dump"):
                item = item.model_dump()
            if not isinstance(item, dict):
                continue
            if not item.get("id"):
                # 모델이 id를 누락했을 때만 입력값으로 보정
                pid = problems[idx].get("id")
                if pid:
                    item = {**item, "id": pid}
            refined.append(item)

        out = RefineOutput(refined_problems=[RefinedProblem.model_validate(x) for x in refined]).model_dump()
        yield Event(state={"refine_output": out})


problem_refine_parallel_agent = ParallelProblemRefineAgent()

