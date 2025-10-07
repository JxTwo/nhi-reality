import logging
from django_celery_beat.models import PeriodicTask, IntervalSchedule
from django.db.utils import OperationalError, ProgrammingError

def register_periodic_fetch():
    try:
        # Every 24 hours
        schedule = IntervalSchedule.objects.filter(
            every=24, period=IntervalSchedule.HOURS
        ).first()
        if not schedule:
            schedule = IntervalSchedule.objects.create(
                every=24, period=IntervalSchedule.HOURS
            )

        PeriodicTask.objects.update_or_create(
            name="Fetch New Content",
            defaults={
                "interval": schedule,           # switch from minutes→hours
                "task": "news.tasks.fetch_new_content",
                "enabled": True,
            },
        )
    except (OperationalError, ProgrammingError) as e:
        logging.warning("Skipped periodic task registration (DB not ready): %s", e)
