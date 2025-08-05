# news/views.py
from django.shortcuts import render
from .models import NewsArticle, Video

def news_list(request):
    articles = NewsArticle.objects.all()
    videos = Video.objects.all()
    combined = sorted(
        list(articles) + list(videos),
        key=lambda obj: obj.published_at,
        reverse=True
    )
    return render(request, "news/news_list.html", {
        "combined_news": combined
    })
