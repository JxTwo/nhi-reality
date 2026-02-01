# news/tasks.py
from __future__ import annotations

import os
import uuid
import logging
from contextlib import contextmanager

from celery import shared_task
from django.core.cache import cache
from django.core.management import call_command
from django.db import connections
from django.db.utils import OperationalError
from django.utils import timezone

from news.models import IngestionStatus, NewsArticle, Video

logger = logging.getLogger(__name__)


def _db_ok() -> bool:
    try:
        connections["default"].cursor()
        return True
    except OperationalError:
        return False


@contextmanager
def cache_lock(key: str, timeout: int):
    """
    Best-effort distributed lock using Django cache (Redis).
    Prevents duplicate runs if beat is accidentally running more than once
    or if tasks overlap.
    """
    token = str(uuid.uuid4())
    acquired = cache.add(key, token, timeout=timeout)
    if not acquired:
        yield False
        return

    try:
        yield True
    finally:
        try:
            if cache.get(key) == token:
                cache.delete(key)
        except Exception:
            logger.exception("Lock release failed for key=%s", key)


def _run_command(name: str, **kwargs) -> dict:
    try:
        logger.info("Running command=%s kwargs=%s", name, kwargs)
        call_command(name, **kwargs)
        return {"status": "ok"}
    except Exception as e:
        logger.exception("Command failed: %s", name)
        return {"status": "error", "error": str(e)}


def _safe_update_status(**fields) -> None:
    """
    Best-effort update of the singleton IngestionStatus row.
    Never raises (we don't want status bookkeeping to crash ingestion).
    """
    try:
        status = IngestionStatus.get()
        for k, v in fields.items():
            setattr(status, k, v)
        status.save(update_fields=list(fields.keys()))
    except Exception:
        logger.exception("Failed to update IngestionStatus fields=%s", list(fields.keys()))


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def fetch_all_news(self) -> dict:
    """
    Runs all fetchers in a deterministic sequence.
    Uses a cache lock to avoid duplicates/overlap.
    Updates IngestionStatus so the UI shows correct freshness.
    """

    if not _db_ok():
        logger.error("fetch_all_news: database unreachable; skipping run")
        # Don't touch IngestionStatus if DB is unreachable.
        return {"status": "skipped", "reason": "db_unreachable"}

    lock_seconds = int(os.getenv("NEWS_FETCH_LOCK_SECONDS", "1800"))  # 30 min
    lock_key = os.getenv("NEWS_FETCH_LOCK_KEY", "lock:news:fetch_all")

    with cache_lock(lock_key, timeout=lock_seconds) as acquired:
        if not acquired:
            logger.info("fetch_all_news: lock not acquired; skipping run")
            # Don't touch IngestionStatus for skipped runs.
            return {"status": "skipped", "reason": "lock_not_acquired"}

        # Mark run started
        started_at = timezone.now()
        _safe_update_status(last_run_started=started_at, last_error=None)

        before_articles = NewsArticle.objects.count()
        before_videos = Video.objects.count()

        logger.info(
            "fetch_all_news: starting (before: articles=%d videos=%d)",
            before_articles,
            before_videos,
        )

        results: dict = {}
        had_any_error = False

        try:
            # Articles
            if os.getenv("NEWS_FETCH_ARTICLES", "1") == "1":
                results["debrief"] = _run_command("fetch_debrief")
                results["liberation_times"] = _run_command("fetch_liberation_times")
                if results["debrief"]["status"] != "ok" or results["liberation_times"]["status"] != "ok":
                    had_any_error = True
            else:
                results["articles"] = {"status": "disabled"}

            # YouTube
            if os.getenv("NEWS_FETCH_YOUTUBE", "1") == "1":
                max_items = int(os.getenv("YOUTUBE_MAX_ITEMS", "50"))
                include_shorts = os.getenv("YOUTUBE_INCLUDE_SHORTS", "0") == "1"
                sleep_s = float(os.getenv("YOUTUBE_API_SLEEP", "0"))

                kwargs = {"max_items": max_items, "sleep": sleep_s}
                if include_shorts:
                    kwargs["include_shorts"] = True

                results["youtube"] = _run_command("fetch_youtube_videos", **kwargs)
                if results["youtube"]["status"] != "ok":
                    had_any_error = True
            else:
                results["youtube"] = {"status": "disabled"}

            after_articles = NewsArticle.objects.count()
            after_videos = Video.objects.count()

            new_articles = after_articles - before_articles
            new_videos = after_videos - before_videos
            added_any = (new_articles + new_videos) > 0

            finished_at = timezone.now()

            # Always record a successful completion *of the task* (even if 0 new).
            # Only bump last_success_with_new if new items were actually added.
            update_fields = {
                "last_success_any": finished_at,
                "last_error": None,
            }
            if added_any:
                update_fields["last_success_with_new"] = finished_at

            # If any subcommand failed but the task kept going, you can decide
            # whether to treat this as "success_any" or as an error.
            # Current behavior: treat as success_any but record error details.
            if had_any_error:
                update_fields["last_error"] = f"One or more subcommands failed: {results}"

            _safe_update_status(**update_fields)

            logger.info(
                "fetch_all_news: complete (after: articles=%d videos=%d new_articles=%d new_videos=%d) results=%s",
                after_articles,
                after_videos,
                new_articles,
                new_videos,
                results,
            )

            return {
                "status": "ok",
                "results": results,
                "new_articles": new_articles,
                "new_videos": new_videos,
                "added_any": added_any,
            }

        except Exception as e:
            # If something unexpected bubbles up, store it and re-raise so Celery retry works.
            logger.exception("fetch_all_news: unexpected failure")
            _safe_update_status(last_error=str(e))
            raise
