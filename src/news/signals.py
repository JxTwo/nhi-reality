import logging
from django_celery_beat.models import PeriodicTask, IntervalSchedule
from django.db.utils import OperationalError, ProgrammingError
from django.apps import apps

def register_periodic_fetch():
    try:
        schedule, _ = IntervalSchedule.objects.get_or_create(
            every=60,
            period=IntervalSchedule.MINUTES,
        )

        PeriodicTask.objects.update_or_create(
            name="Fetch New Content",
            defaults={
                "interval": schedule,
                "task": "news.tasks.fetch_new_content",
            },
        )
    except (OperationalError, ProgrammingError):
        # Database might not be ready during initial migrations
        logging.warning("Skipped periodic task registration (DB not ready)")
