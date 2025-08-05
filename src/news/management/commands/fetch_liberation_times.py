import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime
from django.core.management.base import BaseCommand
from dateutil import parser as date_parser

from news.models import NewsSource, NewsArticle


class Command(BaseCommand):
    help = "Scrape articles from Liberation Times homepage"

    BASE_URL = "https://www.liberationtimes.com"

    def handle(self, *args, **kwargs):
        source, _ = NewsSource.objects.get_or_create(
            name="Liberation Times",
            defaults={"url": self.BASE_URL}
        )

        try:
            resp = requests.get(self.BASE_URL)
            resp.raise_for_status()
        except Exception as e:
            self.stderr.write(f"Failed to fetch homepage: {e}")
            return

        soup = BeautifulSoup(resp.text, "html.parser")

        seen_urls = set()
        new_count = 0

        for tag in soup.find_all("a", href=True):
            href = tag["href"]
            text = tag.get_text(strip=True)
            if not text or not href.startswith("/home/"):
                continue

            full_url = urljoin(self.BASE_URL, href)
            if full_url in seen_urls or NewsArticle.objects.filter(url=full_url).exists():
                continue

            seen_urls.add(full_url)
            article = self.scrape_article(full_url)
            if article:
                NewsArticle.objects.create(
                    title=article["title"][:500],
                    summary=article["summary"],
                    url=full_url,
                    published_at=article["published_at"],
                    source=source,
                    raw_data={
                        "title": article["title"],
                        "summary": article["summary"],
                        "published_at": article["published_at_str"],
                        "raw_html": article["raw_html"],
                    }
                )
                new_count += 1

        self.stdout.write(self.style.SUCCESS(f"Added {new_count} new article(s) from Liberation Times."))

    def scrape_article(self, url):
        try:
            resp = requests.get(url)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            title_tag = soup.find("meta", property="og:title")
            summary_tag = soup.find("meta", property="og:description")
            published_tag = soup.find("meta", property="article:published_time")

            title = title_tag["content"].strip() if title_tag else "(Untitled)"
            summary = summary_tag["content"].strip() if summary_tag else ""
            published_at = date_parser.parse(published_tag["content"]).date() if published_tag else datetime.today().date()

            return {
                "title": title,
                "summary": summary,
                "published_at": published_at,
                "published_at_str": published_at.isoformat(),
                "raw_html": soup.prettify(),
            }
        except Exception as e:
            self.stderr.write(f"Error scraping {url}: {e}")
            return None
