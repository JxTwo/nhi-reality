import requests
from datetime import timezone
from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime
from django.utils.timezone import now
from django.conf import settings
from datetime import timedelta
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

            source, _ = VideoSource.objects.get_or_create(
                name=name,
                channel_id=channel_id
            )

            base_params = {
                "part": "snippet",
                "channelId": channel_id,
                "maxResults": 50,
                "order": "date",
                "type": "video",
                "key": api_key,
            }

            if source.last_fetched_at:
                safe_time = (source.last_fetched_at - timedelta(seconds=1)).replace(microsecond=0, tzinfo=timezone.utc)
                base_params["publishedAfter"] = safe_time.strftime("%Y-%m-%dT%H:%M:%SZ")

            total_fetched = 0
            total_added = 0
            next_page_token = None

            while True:
                params = base_params.copy()
                if next_page_token:
                    params["pageToken"] = next_page_token

                resp = requests.get(YOUTUBE_SEARCH_URL, params=params)
                if resp.status_code != 200:
                    self.stderr.write(f"[{name}] Failed: {resp.text}")
                    break

                data = resp.json()
                items = data.get("items", [])
                next_page_token = data.get("nextPageToken")

                total_fetched += len(items)

                for item in items:
                    snippet = item.get("snippet", {})
                    video_id = item.get("id", {}).get("videoId")
                    if not video_id:
                        continue

                    video_url = f"{YOUTUBE_VIDEO_URL}{video_id}"

                    if apply_filter and not is_relevant_video(snippet):
                        print(f"[{name}] Skipped (not relevant): {snippet.get('title', '')}")
                        continue

                    if Video.objects.filter(url=video_url).exists():
                        continue

                    Video.objects.create(
                        title=snippet.get("title", "")[:500],
                        description=snippet.get("description", ""),
                        url=video_url,
                        published_at=parse_datetime(snippet.get("publishedAt")),
                        source=source,
                        raw_data=item,
                    )
                    total_added += 1
                    print(f"[{name}] Added: {snippet.get('title', '')}")

                if not next_page_token:
                    break

            print(f"[{name}] {total_fetched} videos fetched, {total_added} added")

            source.last_fetched_at = now()
            source.save()
