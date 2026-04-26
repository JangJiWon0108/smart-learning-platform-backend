"""
추천 결과를 사용자에게 친근하게 소개하는 에이전트.

큐레이션 노드가 문제 카드를 준비하는 동안
스트리밍으로 먼저 "N개 찾았어요~" 같은 안내 메시지를 보냅니다.
사용자가 결과를 기다리는 동안 빈 화면 대신 텍스트가 보이게 됩니다.
"""

# ─── 모듈 임포트 ───────────────────────────────────────────────────────────
from google.adk import Agent

from config.gemini_retry import GEMINI_GENERATE_CONTENT_RETRY_CONFIG
from config.properties import Settings

# ─── 설정 로드 ─────────────────────────────────────────────────────────────
settings = Settings()

# ─── 에이전트 정의 ─────────────────────────────────────────────────────────
curator_intro_agent = Agent(
    name="curator_intro_agent",
    model=settings.GEMINI_MODEL_TYPE_CURATOR_INTRO,
    generate_content_config=GEMINI_GENERATE_CONTENT_RETRY_CONFIG,
    # 소개 텍스트를 "curator_intro" 키로 state에 저장합니다
    output_key="curator_intro",
    description="추천 결과를 친화적으로 요약해서 먼저 스트리밍한다.",
    instruction="""
당신은 정보처리기사 실기 문제 추천 결과를 '사용자에게 친화적으로' 소개하는 진행자입니다.

검색어: {rec_query?}
문제 유형: {rec_subject?}
Vertex AI Search 검색 결과: {rec_search_results?}

요구사항:
- 첫 줄에서 "추천 문제를 N개 찾았어요"처럼 친화적으로 시작하세요. (N은 rec_search_results 길이 또는 0)
- 취약점/주제(예: C언어 이중 포인터)를 1문장으로 정리하세요.
- 스포일러 방지를 위해 정답/해설/출력값은 절대 말하지 마세요.
- 마지막에 "아래 카드에서 지문/코드를 확인해요" 같은 다음 행동을 유도하세요.
- 마크다운/코드블록 없이, 자연어 텍스트만 출력하세요.
""",
)
