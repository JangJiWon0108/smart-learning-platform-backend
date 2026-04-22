"""Discovery Engine REST 호출용 AuthorizedSession."""

from __future__ import annotations

import google.auth
from google.auth.transport.requests import AuthorizedSession

from credentials.gcp_auth import get_credentials


def vertex_discovery_authorized_session() -> AuthorizedSession:
    try:
        return AuthorizedSession(get_credentials())
    except (RuntimeError, FileNotFoundError, OSError):
        credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        return AuthorizedSession(credentials)
