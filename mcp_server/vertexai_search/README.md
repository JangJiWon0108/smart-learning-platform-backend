# Vertex AI Search MCP Server

정보처리기사 기출문제 데이터셋의 Vertex AI Search 런타임 검색 기능을 MCP 도구로 노출합니다.

## 실행

```bash
uv run python -m mcp_server.vertexai_search.server
```

## Tools

- `build_filter_expression`: 연도, 회차, 문제 유형 조건을 Discovery Engine filter 문자열로 변환합니다.
- `search_exam_questions`: Discovery Engine에서 기출문제를 검색하고 추천 노드가 바로 쓰는 형태로 파싱합니다.

데이터셋 분류, NDJSON 빌드, 업로드 같은 전처리/운영 작업은 `vertexai_search_etl` 패키지에서 CLI/내부 모듈로 관리합니다.
