"""ASGI entrypoint exposed as `app` so `uvicorn server:app` runs Django."""
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fuelroute.settings")

import django  # noqa: E402

django.setup()

from django.core.asgi import get_asgi_application  # noqa: E402

app = get_asgi_application()

# Eagerly load fuel station dataset on startup so the first request is fast.
from routes.data_loader import ensure_loaded  # noqa: E402

ensure_loaded()
