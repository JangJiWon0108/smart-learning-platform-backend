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
from .llm_agents.recommendation import (
    curator_intro_agent,
    filter_agent,
    question_refine_agent,
)
from .llm_agents.solver import solver_agent
from .llm_agents.visualization import tracer_agent, tracer_input_agent, tracer_intro_agent

# ─── 워크플로우 노드 및 전처리 함수 임포트 ─────────────────────────────────────────────
from smart_learning_agent.nodes.common import intent_router, query_preprocess_func
from smart_learning_agent.nodes.recommendation import build_curator_output_func, vertex_search_func
from smart_learning_agent.nodes.solver import solver_preprocess_func
from smart_learning_agent.nodes.visualization import prepare_tracer_input_func

# ─── 메인 워크플로우 그래프 정의 ───────────────────────────────────────────────────
root_agent = Workflow(
    name="smart_learning_workflow",
    edges=[
        # 공통 전처리 파이프라인 구성 (START → 쿼리 저장 → 이미지 검사 → 쿼리 재구성 → 의도 분석 → 라우팅)
        (
            "START",
            query_preprocess_func,            # 원본 쿼리 저장
            query_rewrite_agent,              # 쿼리 rewrite
            intent_classification_agent,      # 의도 분류
            intent_router,                    # 라우팅
        ),

        # 의도 분류 결과 기반 워크플로우 분기 처리
        (
            intent_router,
            {
                "solver": solver_preprocess_func,           # 문제 풀이
                "recommendation": filter_agent,             # 문제 추천
                "visualization": tracer_input_agent,        # 코드 시각화
                "other": fallback_agent,                    # 지원 불가 안내
            },
        ),

        # Solver 경로: 이미지 및 텍스트 데이터 전처리 후 문제 풀이 수행
        (solver_preprocess_func, solver_agent),

        # Recommendation 경로: 검색 필터 생성 및 Vertex AI 검색 엔진 구동
        (filter_agent, vertex_search_func),

        # Recommendation 경로: 검색 결과 기반 소개 메시지 생성 및 큐레이션 정제 프로세스
        (vertex_search_func, curator_intro_agent, build_curator_output_func, question_refine_agent),

        # Visualization 경로: 코드 추출 및 코드 추적 시각화 프로세스
        (tracer_input_agent, prepare_tracer_input_func, tracer_intro_agent, tracer_agent),
    ],
)
