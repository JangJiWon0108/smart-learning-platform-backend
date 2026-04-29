"""
Discovery Engine REST 호출용 인증 세션.

프로젝트 공통 GCP 자격 증명 우선, 실패 시 Application Default Credentials 폴백.
"""

from __future__ import annotations

# ─── 모듈 임포트 ───────────────────────────────────────────────────────────
import google.auth
from google.auth.transport.requests import AuthorizedSession

from credentials.gcp_auth import get_credentials


# ─── 연결 설정 ─────────────────────────────────────────────────────────────
def vertex_discovery_authorized_session() -> AuthorizedSession:
    """
    Discovery Engine API용 AuthorizedSession 반환.

    Returns:
        GCP 인증이 적용된 AuthorizedSession
    """
    try:
        return AuthorizedSession(get_credentials())
    except (RuntimeError, FileNotFoundError, OSError):
        credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        return AuthorizedSession(credentials)
