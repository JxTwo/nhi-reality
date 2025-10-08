# news/tasks.py
from celery import shared_task
from django.core.management import call_command
from django.utils import timezone

@shared_task
def fetch_new_content():
    # Import inside the task to avoid import cycles during app startup
    from news.models import IngestionStatus, NewsArticle, Video

    status = IngestionStatus.get()
    status.last_run_started = timezone.now()
    status.save(update_fields=["last_run_started"])

    before_articles = NewsArticle.objects.count()
    before_videos = Video.objects.count()

    try:
        # Your existing fetchers
        # call_command("fetch_youtube")
        call_command("fetch_liberation_times")
        call_command("fetch_debrief")

        after_articles = NewsArticle.objects.count()
        after_videos = Video.objects.count()

        new_count = (after_articles - before_articles) + (after_videos - before_videos)

        status.last_success_any = timezone.now()
        if new_count > 0:
            status.last_success_with_new = status.last_success_any
        status.last_error = None
        status.save(update_fields=["last_success_any", "last_success_with_new", "last_error"])

    except Exception as e:
        status.last_error = f"{timezone.now().isoformat()} | {type(e).__name__}: {e}"
        status.save(update_fields=["last_error"])
        raise
