# core/celery.py
import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

app = Celery("core")

# Pull CELERY_* settings from Django settings.py
app.config_from_object("django.conf:settings", namespace="CELERY")

# Find tasks.py in each installed app
app.autodiscover_tasks()
