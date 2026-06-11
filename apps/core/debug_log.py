"""Debug logging helper for media audit session."""
from __future__ import annotations

import json
import time
from pathlib import Path

from django.conf import settings

LOG_PATH = Path(settings.BASE_DIR) / ".cursor" / "debug-ef1f56.log"
SESSION_ID = "ef1f56"


def debug_log(
    *,
    location: str,
    message: str,
    data: dict,
    hypothesis_id: str,
    run_id: str = "audit",
) -> None:
    # #region agent log
    payload = {
        "sessionId": SESSION_ID,
        "runId": run_id,
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data,
        "timestamp": int(time.time() * 1000),
    }
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
    # #endregion
