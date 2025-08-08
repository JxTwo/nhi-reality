from django.core.management.base import BaseCommand
from django_celery_beat.models import IntervalSchedule, PeriodicTask

class Command(BaseCommand):
    help = "Ensures only one 60-minute IntervalSchedule exists, and reassigns any duplicates."

    def handle(self, *args, **options):
        schedules = IntervalSchedule.objects.filter(every=60, period=IntervalSchedule.MINUTES)

        if not schedules.exists():
            self.stdout.write("No 60-minute schedules found. Creating one.")
            IntervalSchedule.objects.create(every=60, period=IntervalSchedule.MINUTES)
            return

        if schedules.count() == 1:
            self.stdout.write(f"Only one schedule found: ID {schedules.first().id}. Nothing to do.")
            return

        self.stdout.write(f"{schedules.count()} schedules found. Cleaning up duplicates...")

        keep = schedules.first()
        for dup in schedules.exclude(id=keep.id):
            PeriodicTask.objects.filter(interval=dup).update(interval=keep)
            self.stdout.write(f"Reassigned PeriodicTasks from ID {dup.id} → {keep.id}")
            dup.delete()
            self.stdout.write(f"Deleted duplicate schedule ID {dup.id}")

        self.stdout.write("Cleanup complete.")
