from config.properties import Settings
from credentials.gcp_auth import init_google_genai
from log import get_logger

settings = Settings()
log = get_logger("smart_learning_agent")

init_google_genai(
    project=settings.PROJECT_ID,
    location=settings.LOCATION,
)

from google.adk import Workflow

from .llm_agents.intent_agent import intent_classification_agent
from .llm_agents.query_rewrite_agent import query_rewrite_agent
from .llm_agents.solver_agent import solver_agent
from .llm_agents.curator_agent import curator_agent
from .llm_agents.curator_intro_agent import curator_intro_agent
from .llm_agents.filter_agent import filter_agent
from .llm_agents.tracer_agent import tracer_agent
from .llm_agents.tracer_intro_agent import tracer_intro_agent
from .llm_agents.fallback_agent import fallback_agent
from .llm_agents.problem_refine_parallel_agent import problem_refine_parallel_agent
from nodes.image_nodes import image_preprocess_func
from nodes.query_rewrite import query_preprocess_func
from nodes.rec_nodes import vertex_search_func
from nodes.router import intent_router
from nodes.solver_nodes import solver_preprocess_func
from nodes.tracer_nodes import language_detect_func

root_agent = Workflow(
    name="smart_learning_workflow",
    edges=[
        ("START", query_preprocess_func, image_preprocess_func, query_rewrite_agent, intent_classification_agent, intent_router),
        (
            intent_router,
            {
                "solver": solver_preprocess_func,
                "recommendation": filter_agent,
                "visualization": language_detect_func,
                "other": fallback_agent,
            },
        ),
        (solver_preprocess_func, solver_agent),
        (filter_agent, vertex_search_func),
        # recommendation: 요약(스트리밍) → 정제/큐레이션(대기) → 카드 결과
        (vertex_search_func, curator_intro_agent),
        (curator_intro_agent, curator_agent, problem_refine_parallel_agent),
        (language_detect_func, tracer_intro_agent, tracer_agent),
    ],
)
