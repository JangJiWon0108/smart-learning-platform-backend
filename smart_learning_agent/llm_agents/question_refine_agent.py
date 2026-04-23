from google.adk import Agent

from config.gemini_retry import GEMINI_GENERATE_CONTENT_RETRY_CONFIG
from config.properties import Settings
from smart_learning_agent.callbacks import build_curation_callback
from smart_learning_agent.schemas.refine_output import RefineOutput

settings = Settings()

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
{curator_output}

위 문제들을 각각 정제하세요.

## 정제 규칙

### refined_question (문제 지문)
- [문제], [cs], [정답], [답], colored by, 정답], 답] 같은 아티팩트를 제거하세요.
- 코드/테이블 데이터는 refined_code로 분리하고 여기서는 제외하세요.
- 문제 번호(예: "6.") 이후의 순수 지문만 남기세요.
- 보기가 있으면(1) 2) 3) 형식) 그대로 유지하세요.

### refined_code (코드 / 테이블)
- 코드나 테이블이 없으면 null을 반환하세요.
- **SQL 테이블 데이터**: 파이프(`|`) 기반 마크다운 표로 변환하세요.
- **SQL 쿼리**: 키워드 대문자, 각 절을 새 줄로 분리해 가독성을 높이세요.
- **Java / C 코드**: 중괄호 기반으로 4칸 들여쓰기를 적용하세요. 함수, 구조체, 클래스 등 최상위 블록 사이에는 빈 줄 1개를 유지하세요.
  - 변수 선언 그룹과 실행 코드(함수 호출, 출력, 연산 등) 사이에 빈 줄 1개를 삽입하세요.
  - 주요 블록(if, for, while, switch) 전후에 빈 줄 1개를 삽입하세요.
  - return 문이 앞 코드와 다른 논리 단계라면 return 앞에 빈 줄 1개를 삽입하세요.
  - 연속되는 출력문(printf, System.out.println 등)은 하나의 단위로 묶되, 그 앞뒤에 빈 줄 1개를 삽입하세요.
- **Python 코드**: 콜론/키워드(def, if, for, while, class 등) 기반으로 4칸 들여쓰기를 적용하세요.
  - 변수 선언 그룹과 실행 코드(함수 호출, 출력, 연산 등) 사이에 빈 줄 1개를 삽입하세요.
  - 주요 블록(if, for, while) 전후에 빈 줄 1개를 삽입하세요.
  - return 문이 앞 코드와 다른 논리 단계라면 return 앞에 빈 줄 1개를 삽입하세요.
  - 연속되는 print 문은 하나의 단위로 묶되, 그 앞뒤에 빈 줄 1개를 삽입하세요.
- 원본 로직은 절대 변경하지 마세요.

### code_language
- Java 코드면 "java", C 코드면 "c", Python이면 "python", SQL이면 "sql"
- 코드/테이블이 없으면 null

## 출력 형식
- refined_problems 배열에 입력 문제 순서대로 모두 포함하세요.
- 각 문제의 id는 입력 문제의 id를 그대로 사용하세요.
- 순수 JSON만 출력하세요. 마크다운 코드블록(```)으로 감싸지 마세요.
""".strip(),
)
