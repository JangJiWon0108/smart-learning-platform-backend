# Agent 워크플로 — 어디부터 읽으면 되나

**한 줄 요약:** 질문이 들어오면 **먼저 라우팅**(어떤 기능 쓸지 고르기) 하고, 그다음 **그 route만 실행**하는 그래프가 돌아갑니다.

- 라우팅 쪽: 전처리 → 재작성 → 의도분류 → `current_route` 결정
- 실행 쪽: `solver` / `recommendation` / `visualization` / `other` 각자 전용 workflow

추천일 때 검색은 MCP로 갑니다 → [mcp.md](mcp.md).  
프론트 스트림은 `/chat/stream` → A2A `POST /stream` 이어 붙기 → [a2a.md](a2a.md).

**맨 먼저 볼 코드:** [`agent.py`](../smart_learning_agent/agent.py) (전체 그래프가 여기 다 모여 있음)

---

## 1. 그래프 두 덩어리

`agent.py` 기준으로 이렇게 나뉩니다.

- `routing_agent`: “지금 사용자가 뭘 원하지?”만 결정
- `*_route_agent`: solver / recommendation / … **실제 일**

### 라우팅 (`routing_agent`)

```text
START
  -> query_preprocess_func
  -> query_rewrite_agent
  -> intent_classification_agent    # 실제 구현: intent_agent
  -> intent_router
```

끝나면 `state["current_route"]`가 정해져서, 다음에 탈 실행 그래프가 갈립니다.

### route 실행 (`*_route_agent`)

```text
solver_route_workflow
  START -> solver_preprocess_func -> solver_agent

recommendation_route_workflow
  START -> filter_agent -> vertex_search_agent -> curator_intro_agent
        -> build_curator_output_func -> question_refine_agent

visualization_route_workflow
  START -> tracer_input_agent -> prepare_tracer_input_func
        -> tracer_intro_agent -> tracer_agent

fallback_route_workflow
  START -> fallback_agent
```

`agent.py`에서 `init_google_genai`, `routing_agent`, `*_route_agent`만 봐도 윤곽은 잡힙니다.

---

## 2. 라우팅 전 공통 전처리

| 순서 | 파일 | 한 일 |
|------|------|--------|
| 1 | [`query_rewrite.py`](../smart_learning_agent/nodes/common/query_rewrite.py) | 맨 앞 `query_preprocess_func` → `original_query` |
| 2 | [`query_rewrite_agent.py`](../smart_learning_agent/llm_agents/common/query_rewrite_agent.py) | 최근 5턴 반영해서 질문 한 문장으로 다시 쓰기 (`rewritten_query`) |
| 3 | [`intent_agent.py`](../smart_learning_agent/llm_agents/common/intent_agent.py) | 의도 분류. 스키마는 [`intent_output.py`](../smart_learning_agent/schemas/intent_output.py) |
| 4 | [`router.py`](../smart_learning_agent/nodes/common/router.py) | `intent_router` → `current_route` 등 세팅, `Event` yield |

**intent 네 가지:** `solver` · `recommendation` · `visualization` · `other`

---

## 3. Solver (문제 풀이·개념·이미지)

**읽는 순서 추천**

1. [`solver_nodes.py`](../smart_learning_agent/nodes/solver/solver_nodes.py)  
2. [`solver_agent.py`](../smart_learning_agent/llm_agents/solver/solver_agent.py)  
3. 이미지까지: [`image.py`](../smart_learning_agent/artifacts/image.py), [`workflow_runner.py`](../smart_learning_agent/runner/workflow_runner.py)의 `prepare_routing_content`, [`route_runner.py`](../smart_learning_agent/runner/route_runner.py)의 `prepare_route_content`

`state["solver_query"]`는 대략 이렇게 만들어집니다.

- 이미지만 → `[이미지에 포함된 문제를 풀어주세요]`
- 이미지+글 → `[이미지 첨부됨] {재작성 질문}`
- 글만 → 재작성 질문 그대로

`solver_agent`는 `solver_output`에 답을 쌓고, 필요하면 `google_search`로 일정·출제 같은 건 조회합니다.

---

## 4. Recommendation (유사 문제)

**읽는 순서 (1→8)**

1. [`filter_agent.py`](../smart_learning_agent/llm_agents/recommendation/filter_agent.py)  
2. [`vertex_search_agent.py`](../smart_learning_agent/llm_agents/recommendation/vertex_search_agent.py)  
3. [`curator_output.py`](../smart_learning_agent/schemas/curator_output.py) (스키마)  
4. [`curator_intro_agent.py`](../smart_learning_agent/llm_agents/recommendation/curator_intro_agent.py)  
5. [`curator_output_nodes.py`](../smart_learning_agent/nodes/recommendation/curator_output_nodes.py)  
6. [`question_refine_agent.py`](../smart_learning_agent/llm_agents/recommendation/question_refine_agent.py)  
7. [`refine_output.py`](../smart_learning_agent/schemas/refine_output.py)  
8. [`problem_cards_callback.py`](../smart_learning_agent/callbacks/problem_cards_callback.py)

**state만 짚으면:**

- `filter_agent` → `vertex_filter_output`
- `vertex_search_agent` + MCP → `rec_search_results` 등 ([mcp.md](mcp.md) 참고)
- `curator_intro` → 잠깐 보여 줄 안내 문장
- `curator_output` → 검색 결과 정리본
- `refine_output` → 지문 다듬은 것
- 콜백에서 합쳐서 → `problem_cards`

---

## 5. Visualization (코드 실행 흐름)

**읽는 순서 (1→6)**

1. [`tracer_input_agent.py`](../smart_learning_agent/llm_agents/visualization/tracer_input_agent.py)  
2. [`tracer_nodes.py`](../smart_learning_agent/nodes/visualization/tracer_nodes.py)  
3. [`tracer_intro_agent.py`](../smart_learning_agent/llm_agents/visualization/tracer_intro_agent.py)  
4. [`tracer_agent.py`](../smart_learning_agent/llm_agents/visualization/tracer_agent.py)  
5. [`tracer_input.py`](../smart_learning_agent/schemas/tracer_input.py), [`tracer_output.py`](../smart_learning_agent/schemas/tracer_output.py)  
6. [`tracer_output_callback.py`](../smart_learning_agent/callbacks/tracer_output_callback.py)

`prepare_tracer_input_func`가 코드·줄번호·언어 state를 정리하고, `tracer_agent`가 단계별 분석을 `tracer_output`에 넣습니다. 콜백은 LLM이 살짝 바꾼 코드를 원본 `tracer_code`에 맞게 되돌립니다.

---

## 6. Other (범위 밖)

[`fallback_agent.py`](../smart_learning_agent/llm_agents/fallback/fallback_agent.py) → `fallback_output`.

---

## 7. Runner (그래프 다 읽은 뒤)

[`workflow_runner.py`](../smart_learning_agent/runner/workflow_runner.py), [`route_runner.py`](../smart_learning_agent/runner/route_runner.py).

라우터용 러너는 대략 이런 모양입니다.

```python
# 의미만 — 실제 필드는 코드 참고
routing_app = App(name=routing_agent.name, root_agent=routing_agent)
routing_runner = InMemoryRunner(app=routing_app)
```

`InMemoryRunner`는 메모리 안에만 세션/아티팩트가 있어서, **재시작하면 날아감**·**인스턴스끼리 공유 없음** 정도만 기억하면 됩니다.

**`/chat/stream` 두 단계**

1. 라우팅 스트림 (`execute_routing_stream`, `StreamingMode.SSE`)
2. 골라진 route의 A2A **`POST /stream`** ([`route_runner.py`](../smart_learning_agent/runner/route_runner.py), [`services.py`](../a2a_remote_routes/services.py))

---

## 파일만 빨리 찾고 싶을 때

**공통:** [workflow_runner.py](../smart_learning_agent/runner/workflow_runner.py) · [query_rewrite.py](../smart_learning_agent/nodes/common/query_rewrite.py) · [query_rewrite_agent.py](../smart_learning_agent/llm_agents/common/query_rewrite_agent.py) · [intent_agent.py](../smart_learning_agent/llm_agents/common/intent_agent.py) · [router.py](../smart_learning_agent/nodes/common/router.py)

**Solver:** [solver_nodes.py](../smart_learning_agent/nodes/solver/solver_nodes.py) · [solver_agent.py](../smart_learning_agent/llm_agents/solver/solver_agent.py)

**Recommendation:** [filter_agent.py](../smart_learning_agent/llm_agents/recommendation/filter_agent.py) · [vertex_search_agent.py](../smart_learning_agent/llm_agents/recommendation/vertex_search_agent.py) · [curator_intro_agent.py](../smart_learning_agent/llm_agents/recommendation/curator_intro_agent.py) · [curator_output_nodes.py](../smart_learning_agent/nodes/recommendation/curator_output_nodes.py) · [question_refine_agent.py](../smart_learning_agent/llm_agents/recommendation/question_refine_agent.py)

**Visualization:** [tracer_input_agent.py](../smart_learning_agent/llm_agents/visualization/tracer_input_agent.py) · [tracer_nodes.py](../smart_learning_agent/nodes/visualization/tracer_nodes.py) · [tracer_intro_agent.py](../smart_learning_agent/llm_agents/visualization/tracer_intro_agent.py) · [tracer_agent.py](../smart_learning_agent/llm_agents/visualization/tracer_agent.py)

**Fallback:** [fallback_agent.py](../smart_learning_agent/llm_agents/fallback/fallback_agent.py)
