"""Temporary debug middleware — enable with DEBUG_REDIRECT=1 in .env."""
from __future__ import annotations

import json
import os
import time
from typing import Callable

from django.http import HttpRequest, HttpResponse

LOG_PATH = os.environ.get("DEBUG_LOG_PATH", "/mnt_data/fpsu/debug-822258.log")


def _log(hypothesis_id: str, message: str, data: dict) -> None:
    # #region agent log
    try:
        payload = {
            "sessionId": "822258",
            "runId": os.environ.get("DEBUG_RUN_ID", "pre-fix"),
            "hypothesisId": hypothesis_id,
            "location": "apps/core/middleware/debug_redirect.py",
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
        }
        with open(LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except OSError:
        pass
    # #endregion


class DebugRedirectMiddleware:
    """Log redirect responses to distinguish Django vs nginx 301."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        if response.status_code in (301, 302, 303, 307, 308):
            _log(
                "H1",
                "django_redirect_response",
                {
                    "path": request.path,
                    "status": response.status_code,
                    "location": response.get("Location", ""),
                    "content_length": len(response.content or b""),
                    "host": request.get_host(),
                    "is_secure": request.is_secure(),
                    "x_forwarded_proto": request.META.get("HTTP_X_FORWARDED_PROTO", ""),
                },
            )
        return response
