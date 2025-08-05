from django.shortcuts import render
from news.models import NewsArticle, Video
from core.utilities import normalize_date

def news_list(request):
    articles = NewsArticle.objects.all()
    videos = Video.objects.all()

    combined = list(articles) + list(videos)

    for item in combined:
        item.content_type = "article" if isinstance(item, NewsArticle) else "video"
        item.normalized_published_at = normalize_date(item)

    sorted_combined = sorted(
        combined,
        key=lambda obj: obj.normalized_published_at,
        reverse=True
    )

    return render(request, "news/news_list.html", {
        "combined_news": sorted_combined
    })
