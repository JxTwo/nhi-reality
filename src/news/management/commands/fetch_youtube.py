# news/management/commands/fetch_youtube.py
import time
import logging
from datetime import timedelta
from typing import Dict, Any, List

import requests
from django.core.management.base import BaseCommand
from django.utils import timezone as tz
from django.utils.dateparse import parse_datetime
from django.conf import settings

from news.models import VideoSource, Video
from ...config.keywords import is_relevant_video
from ...config.youtube_channels import CHANNELS

API = "https://www.googleapis.com/youtube/v3"

def yt_get(path: str, params: Dict[str, Any], timeout=20) -> Dict[str, Any]:
    """YouTube GET with basic retry/backoff for quota/rate/network issues."""
    url = f"{API}/{path}"
    for attempt in range(4):
        r = requests.get(url, params=params, timeout=timeout)
        if r.status_code == 200:
            return r.json()
        # Graceful handling of quotaExceeded & rateLimitExceeded
        try:
            err = r.json()
        except Exception:
            err = {"error": {"message": r.text[:200]}}
        reason = (err.get("error", {}).get("errors", [{}])[0].get("reason") or "").lower()
        if r.status_code in (403, 429) and ("quota" in reason or "rate" in reason):
            sleep = 5 * (2 ** attempt)
            logging.warning("YouTube %s: %s; backing off %ss", reason or r.status_code, err, sleep)
            time.sleep(sleep)
            continue
        raise RuntimeError(f"YouTube error {r.status_code}: {err}")
    raise RuntimeError("YouTube request failed after retries")

class Command(BaseCommand):
    help = "Fetch latest UAP/NHI-related videos from YouTube channels via uploads playlists"

    def handle(self, *args, **kwargs):
        api_key = getattr(settings, "YOUTUBE_API_KEY", None)
        if not api_key:
            self.stderr.write("Missing YOUTUBE_API_KEY in Django settings")
            return

        total_added_all = 0

        for entry in CHANNELS:
            name = entry["name"]
            channel_id = entry["channel_id"]
            apply_filter = entry.get("apply_filter", True)

            source, _ = VideoSource.objects.get_or_create(
                channel_id=channel_id,
                defaults={"name": name},
            )
            if source.name != name:
                source.name = name
                source.save(update_fields=["name"])

            # 1) Get uploads playlist ID (cheap: 1 quota unit)
            ch = yt_get("channels", {
                "part": "contentDetails",
                "id": channel_id,
                "key": api_key,
                "maxResults": 1,
            })
            items = ch.get("items", [])
            if not items:
                self.stderr.write(f"[{name}] channel not found or inaccessible")
                continue
            uploads_pl = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]

            # Watermark: only add strictly newer than this
            watermark = source.last_fetched_at
            # Defensive: if watermark is in the future (clock skew), pull it back by 1 hr
            if watermark and watermark > tz.now() + timedelta(minutes=5):
                watermark = tz.now() - timedelta(hours=1)

            total_fetched = 0
            total_added = 0
            newest_seen = watermark
            next_page = None
            stop_paging = False

            while True:
                # 2) Page through uploads playlist (1 unit/page)
                pl_resp = yt_get("playlistItems", {
                    "part": "contentDetails",            # use contentDetails for videoId + addedAt
                    "playlistId": uploads_pl,
                    "maxResults": 50,
                    "pageToken": next_page or "",
                    "key": api_key,
                })
                pi_items = pl_resp.get("items", [])
                if not pi_items:
                    break

                video_ids = [i["contentDetails"]["videoId"] for i in pi_items if "contentDetails" in i]
                total_fetched += len(video_ids)

                # 3) Batch fetch video details (1 unit/page)
                vids_resp = yt_get("videos", {
                    "part": "snippet",  # title, description, tags, publishedAt
                    "id": ",".join(video_ids),
                    "key": api_key,
                    "maxResults": 50,
                })
                vid_map: Dict[str, Dict[str, Any]] = {v["id"]: v for v in vids_resp.get("items", [])}

                # Sort newest→oldest to respect watermark logic
                def published_at_of(v):
                    p = (v.get("snippet") or {}).get("publishedAt")
                    dt = parse_datetime(p) if p else None
                    if dt and tz.is_naive(dt):
                        dt = tz.make_aware(dt, tz.utc)
                    return dt or tz.now()

                sorted_ids = sorted(video_ids, key=lambda vid: published_at_of(vid_map.get(vid, {})), reverse=True)

                for vid in sorted_ids:
                    v = vid_map.get(vid)
                    if not v:
                        continue
                    snip = v.get("snippet") or {}
                    published_at = published_at_of(v)
                    video_url = f"https://www.youtube.com/watch?v={vid}"

                    # Watermark check (stop when we reach older/equal)
                    if watermark and published_at <= watermark:
                        stop_paging = True
                        continue  # allow loop to finish so we still set newest_seen

                    # Relevance filter using your existing helper
                    if apply_filter and not is_relevant_video({
                        "title": snip.get("title", ""),
                        "description": snip.get("description", ""),
                        "tags": snip.get("tags", []),
                    }):
                        continue

                    # DB duplicate check (url is unique in your model)
                    if Video.objects.filter(url=video_url).exists():
                        continue

                    Video.objects.create(
                        title=(snip.get("title") or "")[:500],
                        description=snip.get("description", "") or "",
                        url=video_url,
                        published_at=published_at,
                        source=source,
                        raw_data=v,
                    )
                    total_added += 1
                    if newest_seen is None or published_at > newest_seen:
                        newest_seen = published_at
                    self.stdout.write(f"[{name}] Added: {snip.get('title','')}")

                if stop_paging or "nextPageToken" not in pl_resp:
                    break
                next_page = pl_resp["nextPageToken"]

            # 4) Advance watermark only if we actually saw something newer
            source.last_fetched_at = newest_seen or source.last_fetched_at or tz.now()
            source.save(update_fields=["last_fetched_at"])

            self.stdout.write(f"[{name}] {total_fetched} videos fetched, {total_added} added")
            total_added_all += total_added

        self.stdout.write(self.style.SUCCESS(f"Total added across all channels: {total_added_all}"))
