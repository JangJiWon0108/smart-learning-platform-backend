"""
FastAPI 서버 진입점.

실행 방법:
  uv run python main.py
  uv run uvicorn api.app:app --reload --app-dir .
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
