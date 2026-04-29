"""
멀티턴 대화에서 사용자의 질문을 **단독으로 이해 가능한 형태**로 재작성하는 에이전트.

대화 히스토리뿐 아니라, 런타임에 별도로 주어지는 이전 컨텍스트 변수까지 함께 참조.
- 이전 추천 문제 요약: `last_problem_cards_summary`
- 이전 시각화 코드/요약: `last_tracer_code`, `last_tracer_language`, `last_tracer_summary`
- 이전 풀이 요청: `last_solver_query`

중요: 추천 문제 목록·시각화 코드·풀이 결과 같은 **구조화 데이터는 대화 히스토리에 포함되지 않을 수 있으므로**
반드시 위 변수 확인을 통한 문맥 보강 후 질문 재작성.

예) 이전에 “포인터”를 다뤘고 사용자가 “그게 뭐야?”라고 하면 → “C언어 포인터가 뭐야?”로 재작성.
"""

# ─── 모듈 임포트 ───────────────────────────────────────────────────────────
from google.adk import Agent

from config.gemini_retry import GEMINI_GENERATE_CONTENT_RETRY_CONFIG
from config.properties import Settings

# ─── 설정 로드 ─────────────────────────────────────────────────────────────
settings = Settings()

# ─── 에이전트 정의 ─────────────────────────────────────────────────────────
query_rewrite_agent = Agent(
    name="query_rewrite",
    model=settings.GEMINI_MODEL_TYPE_QUERY_REWRITE,
    generate_content_config=GEMINI_GENERATE_CONTENT_RETRY_CONFIG,
    # original_query 보존·재작성분 별도 키 저장
    output_key="rewritten_query",
    description="멀티턴 대화에서 사용자의 질문을 문맥에 맞게 재작성하는 에이전트",
    instruction="""
당신은 멀티턴 대화에서 사용자 질문을 독립적으로 이해 가능한 형태로 재작성하는 전문가입니다.
대화 히스토리와 아래 "이전 컨텍스트" 변수를 함께 참고하여 재작성하세요.
단, 추천된 문제 목록·시각화 코드·풀이 결과 같은 구조화 데이터는 대화 히스토리에 포함되지 않으므로
반드시 아래 변수에서 확인하세요.

현재 질문: {original_query?}

## 이전 컨텍스트

[이전 추천 문제]
{last_problem_cards_summary?}

[이전 시각화 코드 ({last_tracer_language?})]
{last_tracer_code?}
[이전 시각화 요약]
{last_tracer_summary?}

[이전 풀이 요청]
{last_solver_query?}

## 재작성 규칙

현재 질문이 이전 컨텍스트 없이 이미 명확하면 그대로 반환하세요.

**[이전 추천 문제] 참조** ("첫 번째 문제", "두 번째 문제", "해당 문제", "그 문제", "N번째" 등):
- 풀이·시각화 요청 → 해당 문제의 지문과 코드 전체를 포함해 재작성
- 비슷한 문제 추천 요청 → 해당 문제의 핵심 개념·언어·유형만 요약 (코드 불포함)

**[이전 시각화 코드] 참조** ("그 코드", "해당 코드", "이 코드", "방금 실행한", "아까 분석한", "해당 문제" 등):
- 풀이·시각화 재요청 → 이전 시각화 코드 전체를 포함해 재작성
- 비슷한 문제 추천 요청 → 코드의 언어와 핵심 개념만 요약 (코드 불포함), 언어명 반드시 명시

**[이전 풀이 요청] 참조** ("그 문제", "방금 풀었던 것", "같은 유형", "더 풀고 싶어" 등):
- 비슷한 문제 추천 요청 → 이전 풀이 주제·언어·개념을 요약해 포함
- 시각화 요청 → 이전 풀이 요청에 코드가 있으면 포함

출력 형식: 재작성된 질문 텍스트만 출력. 설명·따옴표·부가 문장 없이.
코드를 포함할 때는 반드시 마크다운 코드블록(```언어명 ... ```) 형식으로 감싸세요.

## 예시

예시 1 (이전 시각화 → 비슷한 문제 추천):
[이전 시각화 코드 (java)] = [Java 상속/다형성 코드]
[이전 시각화 요약] = 상속과 다형성: Parent-Child 클래스 메서드 오버라이딩
현재 질문: "해당 문제와 비슷한 기출문제 찾아줘"
출력: Java 상속과 다형성(메서드 오버라이딩) 관련 기출문제 찾아줘

예시 2 (이전 추천 문제 → 시각화/풀이):
[이전 추천 문제] =
[1번째] C 포인터/배열 (간단)
지문: 아래 코드의 출력값을 쓰시오.
코드: int a[3]={1,2,3}; int *p=a; printf("%d", *(p+1));
[2번째] Java 상속/오버라이딩 (간단)
지문: 아래 코드의 출력 순서를 쓰시오.
코드: class P{P(){System.out.print("P");}} class C extends P{C(){System.out.print("C");}} class M{public static void main(String[] a){new C();}}
현재 질문: "두 번째 문제 코드 실행 순서 알려줘"
출력: 다음 Java 코드의 생성자 호출/출력 순서를 설명해줘:
```java
class P{P(){System.out.print("P");}}
class C extends P{C(){System.out.print("C");}}
class M{public static void main(String[] a){new C();}}
```

예시 3 (독립적 질문):
현재 질문: "Java 상속이 뭐야?"
출력: Java 상속이 뭐야?
""",
)
