# news/tasks.py
from __future__ import annotations

import os
import uuid
import logging
from contextlib import contextmanager

from celery import shared_task
from django.core.cache import cache
from django.core.management import call_command

logger = logging.getLogger(__name__)


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
    """
    lock_seconds = int(os.getenv("NEWS_FETCH_LOCK_SECONDS", "1800"))  # 30 min
    lock_key = os.getenv("NEWS_FETCH_LOCK_KEY", "lock:news:fetch_all")

    with cache_lock(lock_key, timeout=lock_seconds) as acquired:
        if not acquired:
            logger.info("fetch_all_news: lock not acquired; skipping run")
            return {"status": "skipped", "reason": "lock_not_acquired"}

        logger.info("fetch_all_news: starting")

        results = {}

        # Articles
        if os.getenv("NEWS_FETCH_ARTICLES", "1") == "1":
            results["debrief"] = _run_command("fetch_debrief")
            results["liberation_times"] = _run_command("fetch_liberation_times")
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
        else:
            results["youtube"] = {"status": "disabled"}

        logger.info("fetch_all_news: complete results=%s", results)
        return {"status": "ok", "results": results}
