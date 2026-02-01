import os
import re
import time
import logging
from datetime import timezone

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils.dateparse import parse_datetime
from django.utils import timezone as dj_timezone

from news.models import Video, VideoSource

logger = logging.getLogger(__name__)

YOUTUBE_API = "https://www.googleapis.com/youtube/v3"


def _get_api_key() -> str:
    key = getattr(settings, "YOUTUBE_API_KEY", None) or os.getenv("YOUTUBE_API_KEY")
    if not key:
        raise CommandError("Missing YouTube API key. Set YOUTUBE_API_KEY in settings or env.")
    return key


def _normalize_playlist_id(pid: str | None) -> str | None:
    """
    Normalize playlist ids from various YouTube URL patterns.

    - Standard playlist ids are "PL..."
    - YouTube "show" urls frequently embed "VLPL..." (watch-as-playlist wrapper).
      In that case, the playlist id usable with playlistItems.list is the same
      string with the leading "VL" removed => "PL..."
    """
    if not pid:
        return None
    pid = str(pid).strip()
    if pid.startswith("VLPL"):
        return pid[2:]  # "VLPL..." -> "PL..."
    return pid


def _load_channels():
    """
    Load CHANNELS from news/config/youtube_channels.py

    Supports:
      - name (optional)
      - channel_id (required)
      - playlist_id (optional; can be PL... or VLPL...)
    """
    try:
        from news.config.youtube_channels import CHANNELS  # type: ignore
    except Exception as e:
        raise CommandError(f"Failed to import news.config.youtube_channels.CHANNELS: {e}")

    if not isinstance(CHANNELS, (list, tuple)) or not CHANNELS:
        raise CommandError("CHANNELS must be a non-empty list in news/config/youtube_channels.py")

    norm = []
    for i, ch in enumerate(CHANNELS):
        if not isinstance(ch, dict):
            raise CommandError(f"CHANNELS[{i}] must be a dict")

        name = (ch.get("name") or "").strip()
        channel_id = (ch.get("channel_id") or "").strip()
        playlist_id = _normalize_playlist_id(ch.get("playlist_id"))

        if not channel_id:
            raise CommandError(f"CHANNELS[{i}] is missing channel_id")
        if not name:
            name = channel_id

        norm.append(
            {
                "name": name,
                "channel_id": channel_id,
                "playlist_id": playlist_id,  # None or normalized PL...
            }
        )
    return norm


def _iso8601_duration_to_seconds(s: str) -> int:
    """
    YouTube ISO8601 durations like PT1H2M3S, PT4M, PT59S.
    """
    if not s:
        return 0
    m = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", s)
    if not m:
        return 0
    h = int(m.group(1) or 0)
    mins = int(m.group(2) or 0)
    secs = int(m.group(3) or 0)
    return h * 3600 + mins * 60 + secs


class YouTubeClient:
    def __init__(self, api_key: str, timeout: int = 30):
        self.api_key = api_key
        self.timeout = timeout
        self.session = requests.Session()

    def _get(self, path: str, params: dict) -> dict:
        params = dict(params or {})
        params["key"] = self.api_key
        url = f"{YOUTUBE_API}/{path.lstrip('/')}"
        r = self.session.get(url, params=params, timeout=self.timeout)
        if r.status_code != 200:
            raise CommandError(f"YouTube API error {r.status_code}: {r.text}")
        return r.json()

    def get_channel_uploads_playlist(self, channel_id: str) -> tuple[str, str]:
        """
        Returns (uploads_playlist_id, channel_title)
        """
        data = self._get(
            "channels",
            {
                "part": "snippet,contentDetails",
                "id": channel_id,
                "maxResults": 1,
            },
        )
        items = data.get("items") or []
        if not items:
            raise CommandError(f"No channel found for id={channel_id}")

        ch = items[0]
        channel_title = (ch.get("snippet") or {}).get("title") or channel_id
        uploads = (((ch.get("contentDetails") or {}).get("relatedPlaylists") or {}).get("uploads"))
        if not uploads:
            raise CommandError(f"Could not resolve uploads playlist for channel id={channel_id}")

        return uploads, channel_title

    def list_playlist_items(self, playlist_id: str, max_items: int) -> list[dict]:
        """
        Returns list of playlistItem resources (snippet + contentDetails) for any playlist_id.
        """
        items = []
        page_token = None

        while True:
            batch_size = min(50, max_items - len(items))
            if batch_size <= 0:
                break

            params = {
                "part": "snippet,contentDetails",
                "playlistId": playlist_id,
                "maxResults": batch_size,
            }
            if page_token:
                params["pageToken"] = page_token

            data = self._get("playlistItems", params)
            items.extend(data.get("items") or [])

            page_token = data.get("nextPageToken")
            if not page_token:
                break

        return items[:max_items]

    def videos_details(self, video_ids: list[str]) -> dict[str, dict]:
        """
        Fetch contentDetails (duration) etc. Needed to exclude shorts reliably.
        """
        out: dict[str, dict] = {}
        for i in range(0, len(video_ids), 50):
            chunk = video_ids[i : i + 50]
            data = self._get(
                "videos",
                {
                    "part": "contentDetails,status,snippet",
                    "id": ",".join(chunk),
                    "maxResults": 50,
                },
            )
            for v in data.get("items") or []:
                vid = v.get("id")
                if vid:
                    out[vid] = v
        return out


class Command(BaseCommand):
    help = (
        "Fetch YouTube videos for configured channels. "
        "If playlist_id is configured (PL... or VLPL...), fetch that playlist; "
        "otherwise fetch the channel uploads playlist. Shorts are excluded by default. "
        "Optimization: only call videos.list for videos not already in DB."
    )

    def add_arguments(self, parser):
        parser.add_argument("--max-items", type=int, default=50, help="Max items per channel (default 50)")
        parser.add_argument(
            "--include-shorts",
            action="store_true",
            help="Include shorts (<= 60s). Default behavior excludes shorts.",
        )
        parser.add_argument(
            "--channel-id",
            help="Optional: fetch only this channel_id (must exist in config).",
        )
        parser.add_argument(
            "--sleep",
            type=float,
            default=0.0,
            help="Optional sleep between API calls (seconds).",
        )

    def handle(self, *args, **opts):
        api_key = _get_api_key()
        max_items = int(opts["max_items"])
        include_shorts = bool(opts["include_shorts"])
        only_channel_id = (opts.get("channel_id") or "").strip() or None
        sleep_s = float(opts["sleep"])

        channels = _load_channels()
        if only_channel_id:
            channels = [c for c in channels if c["channel_id"] == only_channel_id]
            if not channels:
                raise CommandError(f"--channel-id {only_channel_id} not found in configured CHANNELS")

        yt = YouTubeClient(api_key=api_key)

        logger.info(
            "Starting YouTube fetch: channels=%d max_items=%d include_shorts=%s",
            len(channels),
            max_items,
            include_shorts,
        )

        total_created = 0
        total_updated = 0
        total_skipped = 0

        for ch in channels:
            channel_id = ch["channel_id"]
            configured_playlist_id = ch.get("playlist_id")

            logger.info(
                "Fetching channel_id=%s (configured name=%s) playlist_id=%s",
                channel_id,
                ch["name"],
                configured_playlist_id or "",
            )

            uploads_playlist_id, channel_title = yt.get_channel_uploads_playlist(channel_id)
            if sleep_s:
                time.sleep(sleep_s)

            # Ensure VideoSource exists; prefer API title as canonical.
            source, _ = VideoSource.objects.get_or_create(
                channel_id=channel_id,
                defaults={"name": channel_title},
            )
            if source.name != channel_title:
                source.name = channel_title
                source.save(update_fields=["name"])

            # If a playlist_id is configured, fetch that playlist; otherwise fetch uploads.
            effective_playlist_id = configured_playlist_id or uploads_playlist_id
            playlist_items = yt.list_playlist_items(effective_playlist_id, max_items=max_items)
            if sleep_s:
                time.sleep(sleep_s)

            # Extract candidate items (newest-first from API).
            extracted = []
            candidate_urls = []
            candidate_video_ids = []

            for it in playlist_items:
                snippet = it.get("snippet") or {}
                content = it.get("contentDetails") or {}

                vid = (content.get("videoId") or "").strip()
                if not vid:
                    continue

                published_raw = snippet.get("publishedAt")
                published_dt = parse_datetime(published_raw) if published_raw else None
                if published_dt and published_dt.tzinfo is None:
                    published_dt = published_dt.replace(tzinfo=timezone.utc)

                title = snippet.get("title") or ""
                description = snippet.get("description") or ""
                url = f"https://www.youtube.com/watch?v={vid}"

                extracted.append(
                    {
                        "video_id": vid,
                        "title": title,
                        "description": description,
                        "url": url,
                        "published_at": published_dt,
                        "playlist_item_raw": it,
                    }
                )
                candidate_urls.append(url)
                candidate_video_ids.append(vid)

            if not extracted:
                logger.info("No playlist items returned for channel_id=%s", channel_id)
                source.last_fetched_at = dj_timezone.now()
                source.save(update_fields=["last_fetched_at"])
                continue

            # --- Optimization: identify which of these are already in DB (by unique url). ---
            existing_urls = set(
                Video.objects.filter(url__in=candidate_urls).values_list("url", flat=True)
            )

            # Keep only "new" items for potential upsert.
            # (We still allow updates of existing records if you want later; right now we treat them as no-op.)
            new_rows = [row for row in extracted if row["url"] not in existing_urls]

            if not new_rows:
                logger.info(
                    "No new videos for channel_id=%s (playlist=%s). Skipping videos.list and DB writes.",
                    channel_id,
                    effective_playlist_id,
                )
                source.last_fetched_at = dj_timezone.now()
                source.save(update_fields=["last_fetched_at"])
                continue

            # Only fetch details for *new* video IDs when we need them to exclude shorts.
            details_by_id = {}
            if not include_shorts:
                new_video_ids = [row["video_id"] for row in new_rows]
                details_by_id = yt.videos_details(new_video_ids)
                if sleep_s:
                    time.sleep(sleep_s)

            created = 0
            updated = 0
            skipped = 0

            # Persist only new items (idempotent; url unique keeps it safe).
            for row in new_rows:
                vid = row["video_id"]

                # Default behavior: exclude shorts (<=60s) when duration is known.
                # If videos.list doesn’t return the video (rare), we keep it.
                if not include_shorts and details_by_id:
                    v = details_by_id.get(vid)
                    if v:
                        dur = ((v.get("contentDetails") or {}).get("duration")) or ""
                        seconds = _iso8601_duration_to_seconds(dur)
                        if seconds and seconds <= 60:
                            skipped += 1
                            continue

                raw_payload = {
                    "playlistItem": row["playlist_item_raw"],
                    "effective_playlist_id": effective_playlist_id,
                }
                if details_by_id and vid in details_by_id:
                    raw_payload["video"] = details_by_id[vid]

                _, was_created = Video.objects.update_or_create(
                    url=row["url"],
                    defaults={
                        "title": row["title"],
                        "description": row["description"],
                        "published_at": row["published_at"] or dj_timezone.now(),
                        "source": source,
                        "raw_data": raw_payload,
                    },
                )

                if was_created:
                    created += 1
                else:
                    updated += 1

            source.last_fetched_at = dj_timezone.now()
            source.save(update_fields=["last_fetched_at"])

            total_created += created
            total_updated += updated
            total_skipped += skipped

            logger.info(
                "Channel done: %s (%s) uploads_playlist=%s effective_playlist=%s playlist_items=%d extracted=%d new=%d created=%d updated=%d skipped(shorts)=%d",
                channel_title,
                channel_id,
                uploads_playlist_id,
                effective_playlist_id,
                len(playlist_items),
                len(extracted),
                len(new_rows),
                created,
                updated,
                skipped,
            )

        logger.info(
            "YouTube fetch complete: total_created=%d total_updated=%d total_skipped=%d",
            total_created,
            total_updated,
            total_skipped,
        )
