# Vertex AI Search MCP Server

정보처리기사 기출문제 데이터셋의 Vertex AI Search 런타임 검색 기능을 MCP 도구로 노출합니다.

## 실행

```bash
# stdio(ADK McpToolset·수동 MCP 클라이언트 테스트용 기본값)
uv run python -m mcp_server.vertexai_search.server

# HTTP(streamable-http) — ADK·client.py 연동 시 필수(127.0.0.1:8200, 메인 API 8000과 구분)
uv run python -m mcp_server.vertexai_search.server --transport streamable-http --host 127.0.0.1 --port 8200

# HTTP(SSE)로 띄울 때 — 필요 시 사용
uv run python -m mcp_server.vertexai_search.server --transport sse --host 127.0.0.1
uv run python -m mcp_server.vertexai_search.server --transport sse -p 9000
```

## Tools

- `build_filter_expression`: 연도, 회차, 문제 유형 조건을 Discovery Engine filter 문자열로 변환합니다.
- `search_exam_questions`: Discovery Engine에서 기출문제를 검색하고 추천 노드가 바로 쓰는 형태로 파싱합니다.

데이터셋 분류, NDJSON 빌드, 업로드 같은 전처리/운영 작업은 `vertexai_search_etl` 패키지에서 CLI/내부 모듈로 관리합니다.
