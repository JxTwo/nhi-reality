import requests
from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime
from django.utils.timezone import now
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

            source, _ = VideoSource.objects.get_or_create(
                name=name,
                channel_id=channel_id
            )

            params = {
                "part": "snippet",
                "channelId": channel_id,
                "maxResults": 50,
                "order": "date",
                "type": "video",
                "key": api_key,
            }

            # Apply publishedAfter to avoid missing older videos
            if source.last_fetched_at:
                params["publishedAfter"] = source.last_fetched_at.isoformat()

            resp = requests.get(YOUTUBE_SEARCH_URL, params=params)
            if resp.status_code != 200:
                self.stderr.write(f"Failed to fetch from {name}: {resp.text}")
                continue

            items = resp.json().get("items", [])
            print(f"[{name}] {len(items)} videos fetched")

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
                print(f"[{name}] Added: {snippet.get('title', '')}")

            # Update fetch time even if no new videos were added
            source.last_fetched_at = now()
            source.save()
