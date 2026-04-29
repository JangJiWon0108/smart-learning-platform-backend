"""
정보처리기사 실기 학습 플랫폼 메인 워크플로우 정의

사용자 입력부터 최종 응답까지의 전체 처리 프로세스 구성
"""

from config.properties import Settings
from credentials.gcp_auth import init_google_genai
from log import get_logger

# 환경 설정 로드 및 로깅 시스템 초기화
settings = Settings()
log = get_logger("smart_learning_agent")

# Vertex AI 인프라 초기화 (에이전트 모듈 임포트 전 선행 필수)
init_google_genai(
    project=settings.PROJECT_ID,
    location=settings.LOCATION,
)

from google.adk import Workflow

# ─── LLM 에이전트 모듈 임포트 ───────────────────────────────────────────────────
from .llm_agents.common import intent_classification_agent, query_rewrite_agent
from .llm_agents.fallback import fallback_agent
from .llm_agents.recommendation import curator_intro_agent, question_refine_agent
from .llm_agents.recommendation.filter_agent import filter_agent
from .llm_agents.recommendation.vertex_search_agent import vertex_search_agent
from .llm_agents.solver import solver_agent
from .llm_agents.visualization import tracer_agent, tracer_input_agent, tracer_intro_agent

# ─── 워크플로우 노드 및 전처리 함수 임포트 ─────────────────────────────────────────────
from smart_learning_agent.nodes.common import intent_router, query_preprocess_func
from smart_learning_agent.nodes.recommendation import build_curator_output_func
from smart_learning_agent.nodes.solver import solver_preprocess_func
from smart_learning_agent.nodes.visualization import prepare_tracer_input_func

# ─── 라우팅 및 Route 단위 워크플로우 정의 ─────────────────────────────────────────────

# 공통 전처리 흐름 정의
routing_agent = Workflow(
    name="smart_learning_router_workflow",
    edges=[
        (
            "START",
            query_preprocess_func,
            query_rewrite_agent,
            intent_classification_agent,
            intent_router,
        ),
    ],
)

# Solver route workflow (A2A route service)
solver_route_agent = Workflow(
    name="solver_route_workflow",
    edges=[
        ("START", solver_preprocess_func, solver_agent),
    ],
)

# Recommendation route: A2A 서비스 + MCP 검색
recommendation_route_agent = Workflow(
    name="recommendation_route_workflow",
    edges=[
        (
            "START",
            # 1) LLM 메타 필터
            filter_agent,
            # 2) MCP search_exam_questions 1회
            vertex_search_agent,
            # 3) 소개 → 카드 구성 → 정제
            curator_intro_agent,
            build_curator_output_func,
            question_refine_agent,
        ),
    ],
)

# Visualization route workflow (A2A route service)
visualization_route_agent = Workflow(
    name="visualization_route_workflow",
    edges=[
        ("START", tracer_input_agent, prepare_tracer_input_func, tracer_intro_agent, tracer_agent),
    ],
)

# Fallback route workflow (A2A route service)
fallback_route_agent = Workflow(
    name="fallback_route_workflow",
    edges=[
        ("START", fallback_agent),
    ],
)

# Route workflow (A2A route service가 노출/실행하는 단위)
route_agents = {
    "solver": solver_route_agent,
    "recommendation": recommendation_route_agent,
    "visualization": visualization_route_agent,
    "other": fallback_route_agent,
}

# 표준 엔트리포인트 이름.
# ADK App에서 사용하는 `root_agent` 파라미터에 주입할 기본 workflow
root_agent = routing_agent
