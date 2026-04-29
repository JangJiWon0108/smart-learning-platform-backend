# Vertex AI Search MCP Server

정보처리기사 기출문제 데이터셋의 Vertex AI Search 런타임 검색 기능을 MCP 도구로 노출합니다.

## 실행

ADK `McpToolset`(streamable-http)과 짝을 맞추려면 별도 터미널에서 MCP 프로세스를 띄웁니다. 바인드 주소는 `VERTEXAI_SEARCH_MCP_URL`(기본 `http://127.0.0.1:8200/mcp`)의 host·port와 동일해야 합니다.

```bash
cd smart-learning-platform-backend
uv run python -m mcp_server.vertexai_search.server
```

## Tools

- `search_exam_questions`: Discovery Engine에서 기출문제를 검색하고 추천 노드가 바로 쓰는 형태로 파싱합니다(요청 시 메타 필터를 Discovery Engine `filter`로 변환해 함께 전송).

데이터셋 분류, NDJSON 빌드, 업로드 같은 전처리/운영 작업은 `vertexai_search_etl` 패키지에서 CLI/내부 모듈로 관리합니다.
