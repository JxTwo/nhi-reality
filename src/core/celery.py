from __future__ import absolute_import, unicode_literals
import os

from celery import Celery
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

app = Celery('core')

app.config_from_object(settings, namespace='CELERY')
app.conf.accept_content = ["json"]
app.conf.task_serializer = "json"
app.conf.result_backend = settings.CELERY_BROKER_URL

# Limits which apps are scanned for Celery tasks
app.autodiscover_tasks(['news'])