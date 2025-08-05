from django.core.management.base import BaseCommand
from news.models import NewsArticle, Video, NewsSource, VideoSource


class Command(BaseCommand):
    help = "Delete all news articles, videos, and sources (for development/testing use only)"

    def handle(self, *args, **kwargs):
        confirm = input("Are you sure you want to delete all News content? This cannot be undone. Type 'yes' to continue: ")

        if confirm.lower() != "yes":
            self.stdout.write(self.style.WARNING("Aborted."))
            return

        num_articles = NewsArticle.objects.count()
        num_videos = Video.objects.count()
        num_sources = NewsSource.objects.count()
        num_video_sources = VideoSource.objects.count()

        NewsArticle.objects.all().delete()
        Video.objects.all().delete()
        NewsSource.objects.all().delete()
        VideoSource.objects.all().delete()

        self.stdout.write(self.style.SUCCESS(f"Deleted {num_articles} articles, {num_videos} videos, {num_sources} news sources, and {num_video_sources} video sources."))
