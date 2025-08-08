import logging
from django_celery_beat.models import PeriodicTask, IntervalSchedule
from django.db.utils import OperationalError, ProgrammingError
from django.apps import apps

def register_periodic_fetch():
    try:
        schedule_qs = IntervalSchedule.objects.filter(every=60, period=IntervalSchedule.MINUTES)
        schedule = schedule_qs.first()
        if not schedule:
            schedule = IntervalSchedule.objects.create(every=60, period=IntervalSchedule.MINUTES)

        PeriodicTask.objects.update_or_create(
            name="Fetch New Content",
            defaults={
                "interval": schedule,
                "task": "news.tasks.fetch_new_content",
            },
        )
    except (OperationalError, ProgrammingError) as e:
        # Database might not be ready during initial migrations
        logging.warning("Skipped periodic task registration (DB not ready): %s", str(e))
