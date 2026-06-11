"""Docker/VPS deployment settings.

nginx terminates TLS — SECURE_SSL_REDIRECT MUST be False here.
Gunicorn serves plain HTTP inside the Docker network.
Used via: DJANGO_SETTINGS_MODULE=project.settings.docker
"""
from .production import *  # noqa: F401, F403
from .production import env

# TLS terminates at nginx; gunicorn listens on plain HTTP.
# Setting True here breaks Docker healthchecks (301 loop → web unhealthy → nginx fails).
SECURE_SSL_REDIRECT = False

# Ensure 'web' service name is in ALLOWED_HOSTS for Docker-internal healthchecks.
_hosts = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
if "web" not in _hosts:
    ALLOWED_HOSTS = _hosts + ["web"]
