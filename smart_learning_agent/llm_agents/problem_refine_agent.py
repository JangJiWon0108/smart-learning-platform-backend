from google.adk import Agent

from config.gemini_retry import GEMINI_GENERATE_CONTENT_RETRY_CONFIG
from config.llm_factory import get_adk_model
from config.properties import Settings
from schemas.refine import RefineOutput

settings = Settings()

problem_refine_agent = Agent(
    name="problem_refine_agent",
    model=get_adk_model(settings, purpose="curator"),
    generate_content_config=GEMINI_GENERATE_CONTENT_RETRY_CONFIG,
    output_schema=RefineOutput,
    output_key="refine_output",
    description="추천 문제 텍스트를 언어별로 정제하는 에이전트",
    instruction="""
당신은 정보처리기사 기출 문제 텍스트를 정제하는 전문가입니다.

curator_output: {curator_output}

위 curator_output의 recommended_problems 각 문제를 정제하세요.

## 정제 규칙

### refined_question (문제 지문)
- [문제], [cs], [정답], [답], colored by, 정답], 답] 같은 아티팩트를 제거하세요.
- 코드/테이블 데이터는 refined_code로 분리하고 여기서는 제외하세요.
- 문제 번호(예: "6.") 이후의 순수 지문만 남기세요.
- 보기가 있으면(1) 2) 3) 형식) 그대로 유지하세요.

### refined_code (코드 / 테이블)
- 코드나 테이블이 없으면 null을 반환하세요.
- **SQL 테이블 데이터**: 파이프(`|`) 기반 마크다운 표로 변환하세요.
  예: `컬럼1 | 컬럼2\n값1 | 값2` → 마크다운 표
- **SQL 쿼리**: 키워드 대문자, 각 절을 새 줄로 분리해 가독성을 높이세요.
- **Java / C 코드**: 중괄호 기반으로 4칸 들여쓰기를 적용하세요.
- **Python 코드**: 콜론/키워드(def, if, for, while, class 등) 기반으로 4칸 들여쓰기를 적용하세요.
- 원본 로직은 절대 변경하지 마세요.

### code_language
- Java 코드면 "java", C 코드면 "c", Python이면 "python", SQL이면 "sql"
- 코드/테이블이 없으면 null

## 출력 형식
- 모든 문제를 refined_problems 배열로 반환하세요.
- 순수 JSON만 출력하세요. 마크다운 코드블록(```)으로 감싸지 마세요.
""",
)
