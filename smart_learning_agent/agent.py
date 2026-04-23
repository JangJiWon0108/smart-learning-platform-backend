"""
스마트 학습 플랫폼의 메인 워크플로우 정의.

사용자 입력부터 최종 응답까지의 전체 처리 흐름을 설정합니다.

전체 흐름:
    START
     ↓
    [전처리] query_preprocess → image_preprocess → query_rewrite → intent_classification → intent_router
     ↓ (라우팅)
    ┌─────────────────────────────────────────────────────────┐
    │ solver         │ recommendation    │ visualization      │ other
    │ (문제풀이)      │ (문제추천)         │ (코드시각화)        │ (폴백)
    ├────────────────┼───────────────────┼────────────────────┼──────────────
    │solver_preprocess│ filter_agent      │ language_detect    │ fallback_agent
    │     ↓          │      ↓           │       ↓            │
    │ solver_agent   │ vertex_search    │ tracer_intro_agent  │
    │                │      ↓           │       ↓            │
    │                │ curator_intro    │ tracer_agent        │
    │                │      ↓           │                    │
    │                │ curator_agent    │                    │
    │                │      ↓           │                    │
    │                │ problem_refine   │                    │
    └────────────────┴───────────────────┴────────────────────┴──────────────
"""

from config.properties import Settings
from credentials.gcp_auth import init_google_genai
from log import get_logger

# 설정 로드 및 로거 초기화
settings = Settings()
log = get_logger("smart_learning_agent")

# Vertex AI 초기화 (에이전트 import 전에 먼저 실행해야 합니다)
init_google_genai(
    project=settings.PROJECT_ID,
    location=settings.LOCATION,
)

from google.adk import Workflow

# ─── 에이전트 import ───────────────────────────────────────────────────────
from .llm_agents.intent_agent import intent_classification_agent
from .llm_agents.query_rewrite_agent import query_rewrite_agent
from .llm_agents.solver_agent import solver_agent
from .llm_agents.curator_agent import curator_agent
from .llm_agents.curator_intro_agent import curator_intro_agent
from .llm_agents.filter_agent import filter_agent
from .llm_agents.tracer_agent import tracer_agent
from .llm_agents.tracer_intro_agent import tracer_intro_agent
from .llm_agents.fallback_agent import fallback_agent
from .llm_agents.question_refine_agent import question_refine_agent

# ─── 노드(전처리 함수) import ─────────────────────────────────────────────
from smart_learning_agent.nodes.query_rewrite import query_preprocess_func
from smart_learning_agent.nodes.rec_nodes import vertex_search_func
from smart_learning_agent.nodes.router import intent_router
from smart_learning_agent.nodes.solver_nodes import solver_preprocess_func
from smart_learning_agent.nodes.tracer_nodes import language_detect_func

# ─── 워크플로우 정의 ──────────────────────────────────────────────────────
root_agent = Workflow(
    name="smart_learning_workflow",
    edges=[
        # 공통 전처리 파이프라인 (모든 요청이 거치는 단계)
        # START → 원본쿼리 저장 → 이미지 확인 → 쿼리 재작성 → 의도 분류 → 라우팅
        (
            "START",
            query_preprocess_func,
            query_rewrite_agent,
            intent_classification_agent,
            intent_router,
        ),

        # 라우터가 의도에 따라 분기합니다
        (
            intent_router,
            {
                "solver": solver_preprocess_func,           # 문제 풀이
                "recommendation": filter_agent,             # 문제 추천
                "visualization": language_detect_func,      # 코드 시각화
                "other": fallback_agent,                    # 지원 불가 안내
            },
        ),

        # solver 경로: 이미지/텍스트 전처리 → 문제 풀이
        (solver_preprocess_func, solver_agent),

        # recommendation 경로: 검색 필터 생성 → Vertex AI 검색
        (filter_agent, vertex_search_func),

        # recommendation 경로: 검색 결과 → 소개 메시지(스트리밍) → 큐레이션 → 문제 정제
        (vertex_search_func, curator_intro_agent),
        (curator_intro_agent, curator_agent, question_refine_agent),

        # visualization 경로: 언어 감지 → 소개 메시지(스트리밍) → 코드 추적
        (language_detect_func, tracer_intro_agent, tracer_agent),
    ],
)
