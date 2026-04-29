"""
Discovery Engine REST 호출용 인증 세션 생성 모듈.

프로젝트 공통 GCP 인증 정보를 우선 사용하고, 없으면 Application Default
Credentials로 Discovery Engine API 호출에 필요한 AuthorizedSession을 만듭니다.
"""

from __future__ import annotations

# ─── 모듈 임포트 ───────────────────────────────────────────────────────────
import google.auth
from google.auth.transport.requests import AuthorizedSession

from credentials.gcp_auth import get_credentials


# ─── 헬퍼 함수 ─────────────────────────────────────────────────────────────
def vertex_discovery_authorized_session() -> AuthorizedSession:
    """
    Discovery Engine REST API 호출에 사용할 인증 세션을 생성합니다.

    Returns:
        GCP 인증 정보가 적용된 AuthorizedSession
    """
    try:
        return AuthorizedSession(get_credentials())
    except (RuntimeError, FileNotFoundError, OSError):
        credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        return AuthorizedSession(credentials)
