import requests
from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime
from django.conf import settings
from news.models import VideoSource, Video
from urllib.parse import urlencode

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEO_URL = "https://www.youtube.com/watch?v="

CHANNELS = [
    {
        "name": "NewsNation",
        "channel_id": "UCXIJgqnII2ZOINSWNOGFThA",  # Ross Coulthart's network
    },
    {
        "name": "Theories of Everything",
        "channel_id": "UCt9S4r2X0yGDU8qrbnOAfvg",  # Curt Jaimungal
    },
]


class Command(BaseCommand):
    help = "Fetch latest UAP/NHI-related videos from YouTube channels"

    def handle(self, *args, **kwargs):
        api_key = getattr(settings, "YOUTUBE_API_KEY", None)
        if not api_key:
            self.stderr.write("Missing YOUTUBE_API_KEY in Django settings")
            return

        for entry in CHANNELS:
            source, _ = VideoSource.objects.get_or_create(
                name=entry["name"], channel_id=entry["channel_id"]
            )

            params = {
                "part": "snippet",
                "channelId": entry["channel_id"],
                "maxResults": 10,
                "order": "date",
                "type": "video",
                "key": api_key,
            }

            resp = requests.get(YOUTUBE_SEARCH_URL, params=params)
            if resp.status_code != 200:
                self.stderr.write(f"Failed to fetch from {entry['name']}: {resp.text}")
                continue

            for item in resp.json().get("items", []):
                video_id = item["id"]["videoId"]
                snippet = item["snippet"]
                video_url = f"{YOUTUBE_VIDEO_URL}{video_id}"

                if Video.objects.filter(url=video_url).exists():
                    continue

                video = Video.objects.create(
                    title=snippet.get("title", "")[:500],
                    description=snippet.get("description", ""),
                    url=video_url,
                    published_at=parse_datetime(snippet.get("publishedAt")),
                    source=source,
                    raw_data=item,
                )
                self.stdout.write(f"Added video: {video.title}")
