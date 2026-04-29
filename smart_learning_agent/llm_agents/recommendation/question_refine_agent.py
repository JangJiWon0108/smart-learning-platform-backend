"""
추천 문제 텍스트 정제 전용 에이전트.

Python 큐레이션 노드가 구성한 문제 목록을 카드 표시용 지문, 코드, 언어 정보로 정리합니다.
"""

# ─── 모듈 임포트 ───────────────────────────────────────────────────────────
from google.adk import Agent

from config.gemini_retry import GEMINI_GENERATE_CONTENT_RETRY_CONFIG
from config.properties import Settings
from smart_learning_agent.callbacks import build_curation_callback
from smart_learning_agent.schemas.refine_output import RefineOutput

# ─── 설정 로드 ─────────────────────────────────────────────────────────────
settings = Settings()

# ─── 에이전트 정의 ─────────────────────────────────────────────────────────
question_refine_agent = Agent(
    name="question_refine_agent",
    model=settings.GEMINI_MODEL_TYPE_QUESTION_REFINE,
    generate_content_config=GEMINI_GENERATE_CONTENT_RETRY_CONFIG,
    output_schema=RefineOutput,
    output_key="refine_output",
    after_agent_callback=build_curation_callback,
    description="추천 문제를 정제(들여쓰기/포맷)하는 에이전트",
    instruction="""
당신은 정보처리기사 기출 문제 텍스트를 정제하는 전문가입니다.

입력 문제 목록:
{curator_output?}

각 문제별 정제 수행.

## 정제 규칙

### refined_question (문제 지문)
- [문제], [cs], [정답], [답], colored by, 정답], 답], 반응형 등 아티팩트 제거
- 코드·테이블 데이터는 refined_code로만 두고 본문에서 제외
- 문제 번호(예: "6.") 이후 순수 지문만 유지
- 보기(1) 2) 3) 형식) 유지
- 개념문제(concept): 원문 붙여쓰기 금지, 문장·목록 가독성 정돈
  - 문장 단위 공백·줄바꿈 보정
  - "1.", "2.", "(1)", "①" 항목: 항목마다 새 줄
  - 괄호 보충: 의미 유지, 문장 흐름용 앞뒤 공백만 정리
  - "다음 설명을 확인하여", "다음 설명에 알맞은" 등 지시문 유지
  - 보기·조건 삭제 금지. 원문에 없는 정답·힌트·해설 추가 금지

### refined_code (코드 / 테이블)
- 코드·테이블 없으면 null
- **SQL 테이블 데이터**: 파이프(|) 기반 마크다운 표
- **SQL 쿼리**: 키워드 대문자, 절마다 새 줄
- **Java / C**: 중괄호 기준 4칸 들여쓰기. 최상위 블록 사이 빈 줄 1
  - 선언 그룹과 실행 코드 사이 빈 줄 1
  - if/for/while/switch 블록 전후 빈 줄 1
  - return이 다른 논리 단계면 return 앞 빈 줄 1
  - 연속 printf/System.out.println 등: 한 덩어리, 앞뒤 빈 줄 1
- **Python**: 콜론·def/if/for/while/class 기준 4칸 들여쓰기
  - 선언 그룹과 실행 코드 사이 빈 줄 1
  - if/for/while 전후 빈 줄 1
  - return 앞 논리 단계 분리 시 빈 줄 1
  - 연속 print: 한 덩어리, 앞뒤 빈 줄 1
- 원본 로직 변경 금지

### code_language
- Java → "java", C → "c", Python → "python", SQL → "sql"
- 코드·테이블 없으면 null

## 출력 형식
- refined_problems: 입력 순서 유지, 전 항목 포함
- id: 입력 문제 id 그대로
- 순수 JSON만. 마크다운 코드블록(```) 금지
""".strip(),
)
