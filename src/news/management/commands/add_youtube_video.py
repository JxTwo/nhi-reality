import re
import requests
from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime
from django.conf import settings
from news.models import Video, VideoSource

YOUTUBE_VIDEO_URL = "https://www.youtube.com/watch?v="
YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/videos"


class Command(BaseCommand):
    help = "Manually add a YouTube video by URL or video ID"

    def add_arguments(self, parser):
        parser.add_argument("url_or_id", help="YouTube video URL or video ID")

    def extract_video_id(self, input_str):
        match = re.search(r"(?:v=|youtu\.be/)([\w-]{11})", input_str)
        if match:
            return match.group(1)
        if re.match(r"^[\w-]{11}$", input_str):
            return input_str
        return None

    def handle(self, *args, **options):
        api_key = getattr(settings, "YOUTUBE_API_KEY", None)
        if not api_key:
            self.stderr.write("Missing YOUTUBE_API_KEY in settings.")
            return

        video_id = self.extract_video_id(options["url_or_id"])
        if not video_id:
            self.stderr.write("Invalid YouTube URL or video ID.")
            return

        # Call YouTube API
        params = {
            "part": "snippet",
            "id": video_id,
            "key": api_key,
        }

        response = requests.get(YOUTUBE_API_URL, params=params)
        if response.status_code != 200:
            self.stderr.write(f"YouTube API error: {response.text}")
            return

        data = response.json()
        items = data.get("items", [])
        if not items:
            self.stderr.write("No video found with that ID.")
            return

        snippet = items[0]["snippet"]
        title = snippet["title"]
        description = snippet.get("description", "")
        published_at = parse_datetime(snippet["publishedAt"])
        channel_title = snippet["channelTitle"]
        channel_id = snippet["channelId"]
        url = f"{YOUTUBE_VIDEO_URL}{video_id}"

        if Video.objects.filter(url=url).exists():
            self.stdout.write("Video already exists in the database.")
            return

        source, _ = VideoSource.objects.get_or_create(name=channel_title, channel_id=channel_id)

        Video.objects.create(
            title=title[:500],
            description=description,
            url=url,
            published_at=published_at,
            source=source,
            raw_data=items[0],
        )

        self.stdout.write(f"✅ Added video: {title} (source: {channel_title})")
