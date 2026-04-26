# Smart Learning Agent Workflow 분석 순서

이 문서는 백엔드의 `smart_learning_agent` 패키지에서 Google ADK 2.0 기반 워크플로우를 코드 분석할 때 어떤 파일과 폴더를 어떤 순서로 보면 좋은지 정리한 문서입니다.

FastAPI 엔드포인트, SSE 응답 변환, 프론트엔드 전송 포맷은 의도적으로 제외합니다. 여기서는 ADK `Workflow`, `Agent`, 노드 함수, runner 실행 경계만 다룹니다.

## 1. 먼저 전체 그래프를 본다

가장 먼저 볼 파일은 `smart_learning_agent/agent.py`입니다.

이 파일이 ADK 앱의 중심입니다. `root_agent = Workflow(...)` 안의 `edges`가 실제 실행 순서를 정의합니다. 다른 파일을 먼저 보면 개별 노드의 역할은 알 수 있지만, 어떤 순서로 연결되는지는 놓치기 쉽습니다.

전체 흐름은 다음과 같습니다.

```text
START
  -> query_preprocess_func          # state["original_query"] 저장
  -> query_rewrite_agent            # 최근 5개 대화 기반 질문 재작성
  -> intent_classification_agent    # 재작성된 질문 기준 의도 분류
  -> intent_router

intent_router 분기:
  solver
    -> solver_preprocess_func       # 재작성된 질문 + has_image -> solver_query
    -> solver_agent

  recommendation
    -> filter_agent                 # 재작성된 질문 -> Vertex 검색 조건
    -> vertex_search_func
    -> curator_intro_agent
    -> build_curator_output_func    # 검색 결과 -> curator_output
    -> question_refine_agent
    -> build_curation_callback

  visualization
    -> tracer_input_agent          # 재작성된 질문에서 코드 추출/언어 감지
    -> prepare_tracer_input_func   # tracer_code_numbered 생성
    -> tracer_intro_agent
    -> tracer_agent
    -> normalize_tracer_callback

  other
    -> fallback_agent               # 재작성된 질문 기준 범위 밖 응답
```

`agent.py`에서 특히 확인할 부분은 세 가지입니다.

- `init_google_genai(...)`: LLM Agent 모듈을 import하기 전에 Vertex AI/GenAI 환경을 초기화합니다.
- `Workflow(name="smart_learning_workflow", edges=[...])`: ADK 워크플로우의 실제 그래프입니다.
- `intent_router` 이후의 dict 분기: `solver`, `recommendation`, `visualization`, `other` 라우트가 여기서 갈라집니다.

## 2. 공통 전처리 흐름을 본다

다음 순서로 보면 사용자 입력이 라우팅되기 전까지 어떻게 state에 쌓이는지 이해할 수 있습니다.

### `nodes/common/query_rewrite.py`

`query_preprocess_func`가 가장 먼저 실행됩니다.

사용자 입력 문자열을 받아 앞뒤 공백을 제거한 뒤 `original_query`로 ADK state에 저장합니다.

```text
입력 query -> state["original_query"]
```

### `llm_agents/common/query_rewrite_agent.py`

최근 대화 5개를 참고해 현재 질문을 독립적으로 이해 가능한 문장으로 재작성합니다.

예를 들어 이전 대화에서 특정 개념을 다룬 뒤 사용자가 “그게 뭐야?”처럼 맥락 의존 질문을 하면, 해당 주제를 포함한 독립형 질문으로 바꿉니다. 이후 라우팅과 각 분기는 이 재작성된 질문을 기준으로 동작합니다.

### `llm_agents/common/intent_agent.py`

재작성된 질문을 보고 의도를 분류합니다.

출력은 `schemas/intent_output.py`의 `IntentOutput` 스키마를 따르며, 결과는 `state["intent_output"]`에 저장됩니다.

가능한 intent는 다음 네 가지입니다.

- `solver`: 문제 풀이, 개념 설명, 이미지 문제 해설, 시험 일정/출제 범위/합격 기준 같은 최신 시험 정보 질의
- `recommendation`: 유사 문제 추천
- `visualization`: 코드 실행 흐름 시각화
- `other`: 서비스 범위 밖 질문

### `nodes/common/router.py`

`intent_router`는 `intent_output.intent` 값을 읽어 ADK `Event`를 yield합니다.

```text
state["current_route"] = intent_output.intent
route = [intent_output.intent]
```

이 `route` 값이 `agent.py`의 분기 dict와 매칭되어 다음 실행 경로가 결정됩니다.

## 3. Solver 분기를 본다

문제 풀이, 개념 설명, 이미지 문제 해설은 Solver 경로로 갑니다.

읽는 순서는 다음이 좋습니다.

1. `nodes/solver/solver_nodes.py`
2. `llm_agents/solver/solver_agent.py`
3. 이미지 입력까지 보려면 `artifacts/image.py`와 `runner/workflow_runner.py`의 `prepare_content`

### `nodes/solver/solver_nodes.py`

`solver_preprocess_func`는 재작성된 질문과 `has_image`를 받아 Solver Agent에 넘길 `solver_query`를 만듭니다.

처리 규칙은 다음과 같습니다.

- 이미지 있고 텍스트 없음: `[이미지에 포함된 문제를 풀어주세요]`
- 이미지와 텍스트 모두 있음: `[이미지 첨부됨] {재작성된 질문}`
- 텍스트만 있음: 재작성된 질문

결과는 `state["solver_query"]`에 저장됩니다.

### `llm_agents/solver/solver_agent.py`

`solver_agent`는 `{solver_query}`를 입력으로 받아 문제 풀이, 개념 설명, 이미지 문제 해설을 생성합니다.

특징은 다음과 같습니다.

- `output_key="solver_output"`
- 필요 시 `google_search` tool 사용
- 정보처리기사 시험 일정, 출제 범위, 합격 기준, 최신 개정, 최신 기술 표준이 필요한 경우 검색 사용

## 4. Recommendation 분기를 본다

문제 추천 경로는 가장 긴 분기입니다. 검색 조건 생성, Vertex AI Search 호출, 추천 결과 구성, 문제 텍스트 정제, UI 카드 생성까지 이어집니다.

읽는 순서는 다음이 좋습니다.

1. `llm_agents/recommendation/filter_agent.py`
2. `schemas/curator_output.py`
3. `nodes/recommendation/vertexai_search_nodes.py`
4. `llm_agents/recommendation/curator_intro_agent.py`
5. `nodes/recommendation/curator_output_nodes.py`
6. `llm_agents/recommendation/question_refine_agent.py`
7. `schemas/refine_output.py`
8. `callbacks/problem_cards_callback.py`

### `llm_agents/recommendation/filter_agent.py`

재작성된 추천 요청에서 Vertex AI Search에 사용할 메타 필터만 만듭니다. 실제 시맨틱 검색어도 이 재작성된 질문을 그대로 사용합니다.

출력은 `VertexFilterOutput`이고 `state["vertex_filter_output"]`에 저장됩니다.

주요 필드는 다음과 같습니다.

- `years`, `rounds`, `question_types`: 메타 필터
- `year_min`, `year_max`: 연도 범위
- `question_numbers`: 문제 번호 필터

### `nodes/recommendation/vertexai_search_nodes.py`

`vertex_search_func`가 `vertex_filter_output`과 재작성된 질문을 받아 실제 Vertex AI Search를 호출합니다.

이 노드에서 외부 검색이 일어나며, 결과는 다음 state로 저장됩니다.

- `rec_search_results`: 검색된 문제 목록
- `rec_query`: 검색에 사용한 재작성된 질문
- `rec_subject`: 검색한 문제 유형 표시값 (`c`, `java`, `python`, `sql`, `concept` 또는 `전체`)

### `llm_agents/recommendation/curator_intro_agent.py`

검색 결과를 바탕으로 사용자에게 먼저 보여줄 짧은 안내 문장을 생성합니다.

이 에이전트는 최종 추천 카드를 만드는 역할이 아니라, 검색과 큐레이션이 이어지는 동안 빈 화면을 줄이기 위한 소개 응답 역할에 가깝습니다.

결과는 `state["curator_intro"]`에 저장됩니다.

### `nodes/recommendation/curator_output_nodes.py`

`rec_search_results`를 `CuratorOutput` 형태로 변환해 최종 추천 문제 목록을 구성합니다.

LLM 호출 없이 검색 결과의 `question`, `year`, `round`, `question_type`, `question_number`, `score`를 그대로 매핑합니다. 출력은 `state["curator_output"]`에 저장됩니다.

### `llm_agents/recommendation/question_refine_agent.py`

`curator_output`의 문제 지문을 정제합니다.

역할은 문제 텍스트에서 `[문제]`, `[cs]`, `colored by` 같은 노이즈를 제거하고, 코드나 SQL 테이블을 `refined_code`로 분리하며, 코드 들여쓰기를 정리하는 것입니다.

출력은 `RefineOutput`이고 `state["refine_output"]`에 저장됩니다.

### `callbacks/problem_cards_callback.py`

`question_refine_agent` 실행 후 `after_agent_callback=build_curation_callback`이 호출됩니다.

이 콜백은 `curator_output`과 `refine_output`을 조합해 프론트엔드가 사용하기 쉬운 `problem_cards`를 만듭니다.

```text
curator_output + refine_output -> state["problem_cards"]
```

FastAPI/SSE를 제외하고도 이 콜백은 ADK workflow의 중요한 후처리 지점입니다.

## 5. Visualization 분기를 본다

코드 실행 흐름 시각화는 Visualization 경로로 갑니다.

읽는 순서는 다음이 좋습니다.

1. `llm_agents/visualization/tracer_input_agent.py`
2. `nodes/visualization/tracer_nodes.py`
3. `llm_agents/visualization/tracer_intro_agent.py`
4. `llm_agents/visualization/tracer_agent.py`
5. `schemas/tracer_input.py`, `schemas/tracer_output.py`
6. `callbacks/tracer_output_callback.py`

### `llm_agents/visualization/tracer_input_agent.py`

`tracer_input_agent`가 재작성된 질문에서 실행 흐름 분석 대상 코드만 추출하고 언어를 감지합니다.

마크다운 코드 블록이 없어도 자연어에 섞인 코드 조각을 분리할 수 있도록 LLM Agent로 처리합니다. 예를 들어 `그냥 아래 코드 순서 모르겠어 a=[1,2] a.append(2)` 같은 입력에서 자연어를 제거하고 Python 코드만 추출합니다.

### `nodes/visualization/tracer_nodes.py`

`prepare_tracer_input_func`가 `tracer_input_agent`의 결과를 후속 Agent가 사용하는 state 형태로 정리합니다.

결과는 다음 state로 저장됩니다.

- `tracer_code`: 추출된 코드
- `tracer_code_numbered`: 줄 번호가 붙은 코드
- `detected_language`: 감지된 언어

### `llm_agents/visualization/tracer_intro_agent.py`

감지된 언어와 코드를 바탕으로 시각화 결과 안내 문장을 먼저 생성합니다.

결과는 `state["tracer_intro"]`에 저장됩니다.

### `llm_agents/visualization/tracer_agent.py`

실제 코드 실행 흐름을 단계별로 분석합니다.

출력은 `TracerOutput`이고 `state["tracer_output"]`에 저장됩니다.

`TracerOutput`에는 다음 정보가 포함됩니다.

- 원본 코드
- 단계별 실행 순서
- 각 줄의 변수 상태
- 변경된 변수 목록
- 콜스택
- C 포인터 메모리 정보
- Java/Python 힙 객체 정보
- 최종 출력과 요약

### `callbacks/tracer_output_callback.py`

`tracer_agent` 실행 후 `normalize_tracer_callback`이 호출됩니다.

LLM이 원본 코드를 미묘하게 바꿔 출력할 수 있기 때문에, 이 콜백은 `tracer_output["original_code"]`와 각 step의 `code`를 `state["tracer_code"]` 기준으로 다시 덮어씁니다.

```text
state["tracer_code"] -> state["tracer_output"]["original_code"]
state["tracer_code"] 각 라인 -> state["tracer_output"]["steps"][i]["code"]
```

## 6. Other 분기를 본다

서비스 범위 밖 질문은 `other`로 분류됩니다.

볼 파일은 `llm_agents/fallback/fallback_agent.py`입니다.

`fallback_agent`는 재작성된 질문 기준으로 질문에 짧게 답하거나 도움 불가를 안내한 뒤, 서비스의 세 가지 핵심 기능으로 유도합니다.

결과는 `state["fallback_output"]`에 저장됩니다.

## 7. Runner는 마지막에 본다

워크플로우 그래프와 각 분기를 이해한 뒤 `runner/workflow_runner.py`를 보면 좋습니다.

이 파일은 FastAPI와 맞닿아 있지만, ADK 관점에서 중요한 부분은 다음 네 가지입니다.

### ADK App 생성

```text
_app = App(
    name=root_agent.name,
    root_agent=root_agent,
)
```

`agent.py`의 `root_agent`를 ADK `App`에 등록합니다.

### InMemoryRunner 생성

```text
workflow_runner = InMemoryRunner(app=_app)
```

현재 구현은 Google ADK의 `InMemoryRunner`를 사용합니다.

`InMemoryRunner` 안에는 인메모리 기반 `session_service`와 `artifact_service`가 포함됩니다. 따라서 별도 DB, Redis, GCS 같은 외부 저장소를 붙이지 않은 상태입니다.

정리하면 현재 저장소 성격은 다음과 같습니다.

- Runner: `InMemoryRunner`
- Session Service: `InMemoryRunner`에 포함된 인메모리 `session_service`
- Session/State: 서버 프로세스 메모리에 저장되는 인메모리 세션과 `session.state`
- Artifact Service: `InMemoryRunner`에 포함된 인메모리 `artifact_service`

구조로 보면 다음과 같습니다.

```text
InMemoryRunner
├─ App / root_agent 실행
├─ session_service
│  └─ 인메모리 세션 저장
│     └─ session.state
└─ artifact_service
   └─ 인메모리 아티팩트 저장
      └─ uploaded_image.jpg
```

이 구조는 개발/단일 서버 실행에는 간단하지만, 서버 재시작 시 세션과 아티팩트가 사라지고 여러 서버 인스턴스 간에는 공유되지 않습니다.

### Content 준비

`prepare_content`는 사용자 입력을 `google.genai.types.Content`로 변환합니다.

ADK 분석 관점에서 볼 부분은 다음입니다.

- 세션이 없으면 생성합니다.
- 세션 state에 `has_image`를 저장합니다.
- 텍스트는 `types.Part(text=...)`로 넣습니다.
- 이미지는 `types.Part(inline_data=...)`로 넣고, `artifact_service`에도 저장합니다.

단, `UploadFile`, MIME 타입 검증, HTTP 415 예외는 FastAPI 경계에 가까우므로 이번 분석에서는 보조 정보로만 보면 됩니다.

### 비스트리밍 실행

```text
workflow_runner.run_async(
    user_id=USER_ID,
    session_id=session_id,
    new_message=content,
    run_config=RunConfig(max_llm_calls=30),
)
```

`execute_agent`는 SSE 없이 ADK event를 그대로 yield합니다. Google ADK workflow 자체를 분석할 때는 이 함수가 가장 깔끔한 실행 진입점입니다.

### 스트리밍 실행

`execute_agent_stream`도 같은 `workflow_runner.run_async(...)`를 사용하지만 `StreamingMode.SSE`를 지정합니다.

이번 문서의 범위에서는 다음 한 줄만 경계로 이해하면 됩니다.

```text
run_config=RunConfig(streaming_mode=StreamingMode.SSE, max_llm_calls=30)
```

SSE 이벤트를 HTTP 응답으로 바꾸는 상위 레이어는 제외합니다.

