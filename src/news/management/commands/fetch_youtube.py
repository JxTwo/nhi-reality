import re
import requests
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime
from django.utils import timezone as tz
from django.conf import settings
from news.models import VideoSource, Video
from ...config.keywords import is_relevant_video
from ...config.youtube_channels import CHANNELS

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEO_URL = "https://www.youtube.com/watch?v="


class Command(BaseCommand):
    help = "Fetch latest UAP/NHI-related videos from YouTube channels"

    def handle(self, *args, **kwargs):
        api_key = getattr(settings, "YOUTUBE_API_KEY", None)
        if not api_key:
            self.stderr.write("Missing YOUTUBE_API_KEY in Django settings")
            return

        for entry in CHANNELS:
            name = entry["name"]
            channel_id = entry["channel_id"]
            apply_filter = entry.get("apply_filter", True)

            # Use channel_id as the unique key; set name as a default (handles channel renames)
            source, _ = VideoSource.objects.get_or_create(
                channel_id=channel_id,
                defaults={"name": name},
            )
            if source.name != name:
                source.name = name
                source.save(update_fields=["name"])

            base_params = {
                "part": "snippet",
                "channelId": channel_id,
                "maxResults": 50,
                "order": "date",
                "type": "video",
                "key": api_key,
            }

            # Only fetch items strictly after last_fetched_at (back off 1s to avoid boundary misses)
            if source.last_fetched_at:
                safe_time = (source.last_fetched_at - timedelta(seconds=1)).astimezone(tz.utc)
                base_params["publishedAfter"] = safe_time.strftime("%Y-%m-%dT%H:%M:%SZ")

            total_fetched = 0
            total_added = 0
            next_page_token = None
            newest_seen = source.last_fetched_at

            while True:
                params = base_params.copy()
                if next_page_token:
                    params["pageToken"] = next_page_token

                resp = requests.get(YOUTUBE_SEARCH_URL, params=params, timeout=20)
                if resp.status_code != 200:
                    self.stderr.write(f"[{name}] Failed: {resp.text}")
                    break

                data = resp.json()
                items = data.get("items", [])
                next_page_token = data.get("nextPageToken")

                total_fetched += len(items)

                for item in items:
                    snippet = item.get("snippet", {})
                    vid = item.get("id", {}).get("videoId")
                    if not vid:
                        continue

                    video_url = f"{YOUTUBE_VIDEO_URL}{vid}"

                    if apply_filter and not is_relevant_video(snippet):
                        self.stdout.write(f"[{name}] Skipped (not relevant): {snippet.get('title','')}")
                        continue

                    if Video.objects.filter(url=video_url).exists():
                        continue

                    published_at = parse_datetime(snippet.get("publishedAt"))
                    # parse_datetime returns aware UTC for RFC3339 with 'Z'; guard just in case
                    if published_at and tz.is_naive(published_at):
                        published_at = tz.make_aware(published_at, tz.utc)

                    Video.objects.create(
                        title=snippet.get("title", "")[:500],
                        description=snippet.get("description", ""),
                        url=video_url,
                        published_at=published_at or tz.now(),
                        source=source,                # ← this drives {{ item.channel_title }} via model property
                        raw_data=item,
                    )
                    total_added += 1
                    if published_at and (newest_seen is None or published_at > newest_seen):
                        newest_seen = published_at

                    self.stdout.write(f"[{name}] Added: {snippet.get('title','')}")

                if not next_page_token:
                    break

            # Advance the watermark to the newest published time we saw; else use now()
            source.last_fetched_at = newest_seen or tz.now()
            source.save(update_fields=["last_fetched_at"])

            self.stdout.write(f"[{name}] {total_fetched} videos fetched, {total_added} added")
