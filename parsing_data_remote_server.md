---
name: parsing-data-remote-server
description: >-
  Implements safe, robust data parsing and import from remote servers (HTTP scraping,
  SSH/SCP file transfer, remote APIs, Cloudinary). Use when fetching data from external
  URLs, scraping HTML pages, transferring files via SSH/SCP, uploading to media APIs,
  or writing Django management commands for ETL pipelines. Enforces proper error
  handling, retry logic, credential management, logging, and bulk DB writes.
---

# Remote Server Data Parsing

## When to Use

Apply this skill whenever the task involves:
- HTTP scraping / downloading files from external URLs
- SSH/SCP file transfer from remote servers
- Uploads to media APIs (Cloudinary, S3, etc.)
- Django management commands that do ETL / data import
- Any code that reads from or writes to a remote host

---

## Phase 1 — Plan Before Code

Before writing a single line:

1. **Map data flow**: source URL/host → transform steps → DB models
2. **Identify failure modes**: network timeout, 4xx/5xx, encoding errors, partial writes
3. **Choose resumability strategy**: idempotent upserts, checkpoint files, or progress flags
4. **Decide on parallelism**: `ThreadPoolExecutor` for I/O-bound; stay sync for small batches

---

## Phase 2 — Credentials & Configuration

### Rules (non-negotiable)

- **Never hardcode** IPs, usernames, passwords, API keys in source files
- Load everything from environment variables via `django-environ` or `os.environ`
- SSH host fingerprint must be in `known_hosts`; **never** use `StrictHostKeyChecking=no`

### Settings pattern

```python
# settings/base.py
REMOTE_SCRAPER = {
    "BASE_URL": env("SCRAPER_BASE_URL"),
    "TIMEOUT": env.int("SCRAPER_TIMEOUT", default=20),
    "MAX_RETRIES": env.int("SCRAPER_MAX_RETRIES", default=3),
    "DELAY": env.float("SCRAPER_DELAY", default=0.5),
}

SSH_CONFIG = {
    "HOST": env("SSH_HOST"),
    "PORT": env.int("SSH_PORT", default=22),
    "USER": env("SSH_USER"),
    "KEY_PATH": env("SSH_KEY_PATH"),
}
```

---

## Phase 3 — HTTP Client

### Required setup

```python
import urllib.request
import urllib.error
import time
import logging

logger = logging.getLogger(__name__)

TIMEOUT = 20  # always set; never omit


def fetch_html(url: str, retries: int = 3, delay: float = 1.0) -> str:
    """Fetch URL with retry/backoff. Returns HTML string or raises."""
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(url, timeout=TIMEOUT) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            logger.warning("HTTP %s on %s (attempt %d/%d)", exc.code, url, attempt, retries)
            if exc.code in (429, 503):
                time.sleep(delay * attempt)  # exponential backoff
            elif 400 <= exc.code < 500:
                raise  # client errors are not retryable
        except (urllib.error.URLError, OSError) as exc:
            logger.warning("Network error on %s (attempt %d/%d): %s", url, attempt, retries, exc)
            time.sleep(delay * attempt)
    raise RuntimeError(f"Failed to fetch {url} after {retries} attempts")
```

### Key rules

- Always pass `timeout=` — default is **None** (blocks forever)
- Retry only on transient errors (5xx, timeout, connection reset); not on 4xx
- Exponential backoff: `sleep(delay * attempt)`
- Decode with `errors="replace"` but **log a warning** when replacements occur
- Use `User-Agent` header if the server blocks default Python UA

---

## Phase 4 — SSH / SCP File Transfer

```python
import subprocess
import shlex

def scp_download(remote_path: str, local_path: str, cfg: dict) -> None:
    """Download a file via SCP. Raises subprocess.CalledProcessError on failure."""
    cmd = [
        "scp",
        "-P", str(cfg["PORT"]),
        "-i", cfg["KEY_PATH"],
        "-o", "BatchMode=yes",           # fail fast, no interactive prompts
        "-o", "ConnectTimeout=15",
        # NO StrictHostKeyChecking=no — add host to known_hosts instead
        f"{cfg['USER']}@{cfg['HOST']}:{remote_path}",
        local_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error("SCP failed (rc=%d): %s", result.returncode, result.stderr)
        result.check_returncode()  # raises CalledProcessError
```

### Security checklist for SSH

- [ ] Host fingerprint is in `~/.ssh/known_hosts` (or project `known_hosts` file)
- [ ] Auth via private key (`-i KEY_PATH`), not password
- [ ] `StrictHostKeyChecking` is **not** disabled
- [ ] `SSH_HOST`, `SSH_PORT`, `SSH_USER`, `SSH_KEY_PATH` come from env vars only
- [ ] Principle of least privilege: use a dedicated deploy user, not `root`

---

## Phase 5 — HTML Parsing

```python
from bs4 import BeautifulSoup

def parse_page(html: str, url: str) -> dict:
    """Parse HTML page; return dict or raise ValueError on unexpected structure."""
    soup = BeautifulSoup(html, "lxml")

    title_tag = soup.find("h1", class_="page-title")
    if title_tag is None:
        raise ValueError(f"Expected <h1.page-title> not found in {url}")

    return {
        "title": title_tag.get_text(strip=True),
        "body": str(soup.find("div", class_="article-body") or ""),
    }
```

### Rules

- Always specify parser explicitly: `"lxml"` (fast) or `"html.parser"` (stdlib)
- Validate required elements exist; raise `ValueError` with URL context — don't silently return `None`
- Do not use fragile regex on HTML; use `BeautifulSoup` selectors
- Sanitize extracted HTML before DB write (use `bleach.clean` with an allowlist)

---

## Phase 6 — Error Handling

### Anti-patterns

```python
# ❌ swallows all errors — impossible to debug
except Exception:
    return None

# ❌ logs but hides original traceback
except Exception as exc:
    print(exc)
    return None
```

### Correct pattern

```python
# ✅ narrow exception types + log with exc_info
except urllib.error.URLError as exc:
    logger.error("Network error fetching %s: %s", url, exc, exc_info=True)
    raise

# ✅ broad except only at top level, with full context
except Exception as exc:
    logger.error(
        "Unexpected error processing item pk=%s url=%s",
        item.pk, url, exc_info=True
    )
    failed.append(item.pk)
    # continue to next item — don't abort entire import
```

### Hierarchy

| Exception type | Action |
|---------------|--------|
| `HTTPError` 4xx | Log ERROR, skip item, continue |
| `HTTPError` 5xx / timeout | Retry with backoff; log WARNING per attempt, ERROR after exhaustion |
| `ValueError` (bad parse) | Log ERROR with item context, skip |
| Cloudinary/API error | Log ERROR with full response, skip |
| DB integrity error | Log CRITICAL, rollback batch, raise |

---

## Phase 7 — Database Writes

### Rules

- Prefer `bulk_create` / `bulk_update` over per-row `save()` in loops
- Use `update_or_create` for small sets or upsert logic
- Wrap batches in `transaction.atomic()`, not the entire import loop
- Never use a single transaction spanning thousands of rows (long lock, huge rollback)

```python
from django.db import transaction

BATCH = 500

def save_articles(records: list[dict]) -> None:
    objs = [Article(**r) for r in records]
    with transaction.atomic():
        Article.objects.bulk_create(
            objs,
            update_conflicts=True,
            update_fields=["title", "body", "updated_at"],
            unique_fields=["joomla_id"],
            batch_size=BATCH,
        )
```

### Pagination: keyset over OFFSET

```python
# ❌ OFFSET degrades on large tables
Article.objects.all()[offset : offset + BATCH]

# ✅ keyset pagination
last_pk = 0
while True:
    batch = list(Article.objects.filter(pk__gt=last_pk).order_by("pk")[:BATCH])
    if not batch:
        break
    # process batch
    last_pk = batch[-1].pk
```

---

## Phase 8 — Logging

Replace all `print()` calls in management commands with the standard logger:

```python
import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    def handle(self, *args, **options):
        logger.info("Import started")
        # ...
        logger.info("Done: created=%d updated=%d failed=%d", created, updated, failed)
```

`settings/base.py` logging config (minimum):

```python
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "apps": {"level": "DEBUG", "propagate": True},
    },
}
```

---

## Phase 9 — Rate Limiting & Politeness

```python
import time

POLITENESS_DELAY = 0.5  # seconds between requests to same host

for url in urls:
    try:
        html = fetch_html(url)
        process(html)
    except Exception:
        pass  # already logged inside fetch_html
    finally:
        time.sleep(POLITENESS_DELAY)
```

- Respect `Retry-After` header on 429 responses
- Do not parallelize requests to the same host without rate limiting
- Add `User-Agent: <project-name>/<version> (+contact-email)` to identify the bot

---

## Phase 10 — Security Checklist

Before committing any parsing/import code:

- [ ] No credentials, IPs, or tokens in source files
- [ ] All secrets loaded from env vars
- [ ] `StrictHostKeyChecking` is **not** disabled
- [ ] Parsed HTML is sanitized with `bleach` before DB write
- [ ] No `eval()`, `exec()`, or `pickle.loads()` on remote data
- [ ] File paths from remote data are validated/sanitized (path traversal)
- [ ] Cloudinary/API errors are caught and return structured error responses
- [ ] Sensitive temp files (`.cnf`, key copies) are removed in `finally` block

---

## Phase 11 — Management Command Template

```python
import logging
from django.core.management.base import BaseCommand
from django.db import transaction

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Import data from remote source"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--limit", type=int, default=0)

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        limit = options["limit"]

        stats = {"created": 0, "updated": 0, "failed": 0, "skipped": 0}

        items = self._fetch_items(limit=limit)
        for item in items:
            try:
                result = self._process_item(item, dry_run=dry_run)
                stats[result] += 1
            except Exception:
                logger.error("Failed item %s", item, exc_info=True)
                stats["failed"] += 1

        logger.info(
            "Import complete: %s",
            " | ".join(f"{k}={v}" for k, v in stats.items()),
        )
        if dry_run:
            logger.info("DRY RUN — no changes written")

    def _fetch_items(self, limit: int) -> list:
        raise NotImplementedError

    def _process_item(self, item, dry_run: bool) -> str:
        """Must return one of: 'created', 'updated', 'skipped'."""
        raise NotImplementedError
```

---

## Common Pitfalls Reference

| Pitfall | Consequence | Fix |
|---------|-------------|-----|
| No `timeout=` in `urlopen` | Process hangs indefinitely | Always set `timeout=20` |
| `StrictHostKeyChecking=no` | MITM vulnerability | Add host to `known_hosts` |
| Hardcoded SSH host/user | Credential leak in repo | Move to env vars |
| `except Exception: return None` | Silent data loss | Log ERROR + re-raise or collect |
| Single `save()` per row in loop | N×DB round trips | Use `bulk_update` with batches |
| One `atomic()` for entire import | Long lock + huge rollback | Wrap per-batch only |
| OFFSET pagination | O(n²) full table scans | Use keyset (filter by last PK) |
| `print()` in management commands | Not captured by Sentry/log aggregators | Use `logger.*()` |
| `bulk_create(ignore_conflicts=True)` without `unique_together` | Duplicates on re-run | Add unique constraint first |
| Storing URL string in `CloudinaryField` | Template render broken | Store public_id consistently |
