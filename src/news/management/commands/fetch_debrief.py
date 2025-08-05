import feedparser
from django.core.management.base import BaseCommand
from news.models import NewsSource, NewsArticle
from datetime import datetime
from dateutil import parser as date_parser

class Command(BaseCommand):
    help = "Fetch latest articles from The Debrief RSS feed"

    def handle(self, *args, **kwargs):
        source, _ = NewsSource.objects.get_or_create(
            name="The Debrief",
            defaults={"url": "https://thedebrief.org/feed/"}
        )

        feed = feedparser.parse(source.url)

        new_count = 0

        for entry in feed.entries:
            url = entry.get("link")
            if NewsArticle.objects.filter(url=url).exists():
                continue

            published = entry.get("published", "")
            try:
                published_at = date_parser.parse(published).date()
            except Exception:
                published_at = datetime.today().date()

            NewsArticle.objects.create(
                title=entry.get("title", "")[:500],
                summary=entry.get("summary", ""),
                url=url,
                published_at=published_at,
                source=source,
                raw_data=entry
            )
            new_count += 1

        self.stdout.write(self.style.SUCCESS(f"Added {new_count} new article(s) from The Debrief."))
