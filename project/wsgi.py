"""WSGI config for project."""
import os
from pathlib import Path

import environ

# Load .env before choosing settings module (gunicorn often omits explicit export).
_env_file = Path(__file__).resolve().parent.parent / ".env"
if _env_file.exists():
    environ.Env.read_env(str(_env_file))

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings.develop")

application = get_wsgi_application()
