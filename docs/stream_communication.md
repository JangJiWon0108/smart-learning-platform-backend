# Stream 전송 정리 (백엔드 <-> 프론트엔드)

프론트엔드와 백엔드는 채팅 응답을 실시간으로 보여주기 위해 SSE(Server-Sent Events) 형식의 스트림 통신을 사용한다. 요청은 일반 `POST` 요청으로 시작하고, 응답 바디는 `text/event-stream`으로 열린 상태를 유지하면서 처리 상태, 텍스트 조각, 최종 구조화 데이터를 순차 전송한다.

## 핵심 흐름

프론트엔드는 `/chat/stream`으로 요청을 한 번 보낸다. 백엔드는 그 연결을 닫지 않고, ADK Workflow에서 발생하는 이벤트를 SSE 형식으로 하나씩 내려준다.

```text
사용자 질문
  ↓
Frontend → POST /chat/stream
  ↓
FastAPI → execute_agent_stream()
  ↓
ADK Workflow 노드 실행
  ↓
FastAPI가 ADK Event를 SSE type으로 변환
  ↓
Frontend가 type에 따라 상태 말풍선, 답변 청크, 추천 카드, 시각화 결과를 표시
```

즉, 프론트가 중간에 새 요청을 보내는 것이 아니라 **요청 하나 안에서 `state`, `chunk`, `stream_end`, 최종 결과, `done`이 순서대로 온다.**

## 이벤트 타입 요약

| type | 백엔드가 보내는 의미 | 프론트에서 하는 일 |
|---|---|---|
| `state` | 현재 실행 중인 노드 이름 전달 | 상태 말풍선/로딩 문구를 바꾼다 |
| `chunk` | 사용자에게 보여줄 텍스트 조각 전달 | 채팅 말풍선에 텍스트를 이어 붙인다 |
| `stream_end` | 한 노드의 텍스트 스트리밍 종료 | 해당 말풍선 스트리밍이 끝났다고 처리한다 |
| `curation` | 추천 문제 최종 결과 전달 | 추천 카드 UI를 보여준다 |
| `tracer` | 코드 실행 흐름 최종 결과 전달 | 시각화 UI를 보여준다 |
| `error` | 오류 메시지 전달 | 오류 말풍선을 보여준다 |
| `done` | 전체 stream 요청 종료 | 요청을 마무리한다 |

`state`는 노드 완료가 아니라 **노드 진입/진행 상태**에 가깝다. 새 노드를 처음 만나면 백엔드가 한 번 보낸다.

`chunk`는 실제 답변 텍스트다. 모든 노드에서 나오는 것이 아니라 `_STREAM_NODES`에 포함된 노드에서만 나온다.

## 백엔드에서 보내는 위치

모든 이벤트 전송은 `api/app.py`의 `/chat/stream` 안에 있는 `event_generator()`에서 이루어진다.

| type | 보내는 위치 | 조건 |
|---|---|---|
| `state` | `if node_name and node_name not in emitted_nodes:` | 새 노드 이름을 처음 만났을 때 |
| `chunk` | `if is_stream_node and event.content:` | 현재 노드가 스트리밍 허용 노드이고 텍스트가 있을 때 |
| `stream_end` | `node_name` 전환 또는 `not event.partial` 처리 | `chunk`를 보내던 노드가 끝났을 때 |
| `curation` | `_build_curation_payload(state)` 이후 | 추천 결과가 state에 있을 때 |
| `tracer` | `state.get("tracer_output")` 확인 이후 | 시각화 결과가 state에 있을 때 |
| `error` | `except Exception` 또는 visualization 실패 분기 | 처리 중 오류가 났을 때 |
| `done` | `finally` | 성공/실패와 관계없이 마지막 |

현재 `chunk`를 보낼 수 있는 노드는 아래 네 개다.

```py
_STREAM_NODES = {
    "solver_agent",
    "fallback_agent",
    "curator_intro_agent",
    "tracer_intro_agent",
}
```

추천 카드(`curation`)와 코드 실행 흐름(`tracer`)은 토큰 조각으로 뿌리지 않고, 최종 구조화 데이터로 한 번에 보낸다.

## 예시: "C언어 이중 포인터 문제 알려줘"

아래 예시는 사용자의 질문이 recommendation route로 분류됐다고 가정한 전체 흐름이다.

사용자 질문:

```text
C언어 이중 포인터 문제 알려줘
```

ADK Workflow의 recommendation 경로는 `smart_learning_agent/agent.py`에 아래 순서로 정의되어 있다.

```text
START
  ↓
query_preprocess_func
  ↓
query_rewrite_agent
  ↓
intent_classification_agent
  ↓
intent_router
  ↓ recommendation route
filter_agent
  ↓
vertex_search_func
  ↓
curator_intro_agent
  ↓
build_curator_output_func
  ↓
question_refine_agent
  ↓
최종 curation 이벤트
  ↓
done
```

### 노드별 스트림 전송 흐름

| 순서 | 실행 노드 | 백엔드가 보내는 이벤트 | 프론트에서 보이는 것 | 설명 |
|---:|---|---|---|---|
| 1 | `query_preprocess_func` | `state` | 요청을 준비/처리 중인 상태 문구 | 원본 질문을 state에 저장 |
| 2 | `query_rewrite_agent` | `state` | 질문을 다듬는 중이라는 상태 문구 | 최근 5개 대화 맥락을 참고해 현재 질문 재작성 |
| 3 | `intent_classification_agent` | `state` | 질문 의도를 파악하는 중이라는 상태 문구 | 질문을 `solver`, `recommendation`, `visualization`, `other` 중 하나로 분류 |
| 4 | `intent_router` | `state` | 의도 파악/라우팅 상태 문구 | `recommendation` route 선택 |
| 5 | `filter_agent` | `state` | 추천 결과를 필터링하는 중이라는 상태 문구 | 검색 조건 생성 |
| 6 | `vertex_search_func` | `state` | 관련 문제를 검색하는 중이라는 상태 문구 | Vertex AI Search로 관련 문제 검색 |
| 7 | `curator_intro_agent` | `state` + `chunk` | 안내 문장이 채팅 말풍선에 실시간 출력 | 추천 카드 생성 전 짧은 안내 문장 생성 |
| 8 | `curator_intro_agent` 종료 | `stream_end` | 현재 안내 문장 스트리밍 종료 | 전체 요청 종료가 아니라 intro 문장만 종료 |
| 9 | `build_curator_output_func` | `state` | 결과를 정리하는 중이라는 상태 문구 | 검색 결과를 추천 카드용 데이터로 정리 |
| 10 | `question_refine_agent` | `state` | 문제를 다듬는 중이라는 상태 문구 | 추천 문제 내용을 보기 좋게 정제 |
| 11 | workflow 완료 후 | `curation` | 추천 카드 UI 표시 | 최종 추천 결과 데이터 전송 |
| 12 | 마지막 | `done` | 요청 종료 | 전체 `/chat/stream` 종료 |

여기서 모든 노드는 `state` 이벤트를 받을 수 있다. 하지만 `chunk`는 모든 노드에서 나오지 않는다. 현재 recommendation 흐름에서는 `_STREAM_NODES`에 포함된 `curator_intro_agent`만 텍스트 조각을 `chunk`로 보낸다.

### 실제 SSE 이벤트 예시

실제 전송은 아래처럼 `data: ...` 블록이 순서대로 이어진다.

```text
data: {"type":"state","node":"query_preprocess_func"}

data: {"type":"state","node":"query_rewrite_agent"}

data: {"type":"state","node":"intent_classification_agent"}

data: {"type":"state","node":"intent_router"}

data: {"type":"state","node":"filter_agent"}

data: {"type":"state","node":"vertex_search_func"}

data: {"type":"state","node":"curator_intro_agent"}

data: {"type":"chunk","text":"C언어 이중 포인터를 연습할 수 있는 "}

data: {"type":"chunk","text":"문제를 찾아보고 있어요. "}

data: {"type":"chunk","text":"주소 참조와 간접 참조를 중심으로 추천해드릴게요."}

data: {"type":"stream_end"}

data: {"type":"state","node":"build_curator_output_func"}

data: {"type":"state","node":"question_refine_agent"}

data: {"type":"curation","route":"recommendation","title":"맞춤 추천 문제 카드","problemCards":[...],"message":null}

data: {"type":"done"}

```

프론트에서 사용자가 체감하는 화면 변화는 아래와 같다.

```text
1. "질문을 정리하는 중이에요..."
2. "질문 의도를 파악하는 중이에요..."
3. "추천 결과를 필터링하는 중이에요..."
4. "관련 문제를 검색하는 중이에요..."
5. 채팅 말풍선에 안내 문장 출력
   "C언어 이중 포인터를 연습할 수 있는 문제를 찾아보고 있어요..."
6. 안내 문장 스트리밍 종료
7. "문제를 다듬는 중이에요..."
8. 추천 카드 UI 표시
```

### `state`와 `chunk` 차이

이 예시에서 핵심은 아래와 같다.

```text
state
  = "지금 어떤 노드를 처리 중인가"를 알려주는 상태 이벤트
  = 노드 완료 이벤트가 아니라 노드 진입/진행 표시
  = 프론트는 로딩 문구 변경에 사용

chunk
  = 사용자에게 실제로 보여줄 텍스트 조각
  = _STREAM_NODES에 포함된 노드에서만 전송
  = 프론트는 채팅 말풍선에 이어 붙임

stream_end
  = chunk를 보내던 한 노드의 텍스트 스트리밍 종료
  = 전체 요청 종료가 아님

curation
  = recommendation route의 최종 결과 데이터
  = 프론트는 추천 카드 UI로 렌더링

done
  = 전체 /chat/stream 요청 종료
```

즉, "C언어 이중 포인터 문제 알려줘" 예시에서 `curator_intro_agent`가 보낸 `chunk`는 최종 추천 카드가 아니다. 사용자가 기다리는 동안 먼저 보여주는 안내 문장이고, 실제 추천 결과는 뒤에서 `curation` 이벤트로 한 번에 전달된다.

## 변경 시 체크리스트

- 새 노드의 텍스트를 실시간으로 보여줘야 하면 백엔드 `_STREAM_NODES`에 노드 이름을 추가한다.
- 새 이벤트 타입을 추가하면 프론트에서 해당 타입을 받아 어떻게 보여줄지 정한다.
- 새 workflow node를 추가하면 프론트 상태 말풍선에 표시할 문구를 정한다.
- 구조화 데이터는 `chunk`로 쪼개지 말고 별도 `type` 이벤트로 완성본을 전송한다.
- SSE 블록은 반드시 `data: ...\n\n` 형식을 유지한다.
- JSON에는 한글이 포함될 수 있으므로 백엔드 전송 시 필요한 곳에 `ensure_ascii=False`를 유지한다.
- 스트림 종료 신호가 누락되지 않도록 정상/오류 경로 모두에서 `done`을 보낸다.
