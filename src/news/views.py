from django.core.paginator import Paginator
from django.shortcuts import render
from news.models import NewsArticle, Video
from core.utilities import normalize_date

def news_list(request):
    f = request.GET.get("type", "all").lower()
    page_number = request.GET.get("page")

    # Precompute counts for the filter pills
    article_count = NewsArticle.objects.count()
    video_count = Video.objects.count()
    counts = {"all": article_count + video_count, "articles": article_count, "videos": video_count}

    # Pull (up to) 100 of each, then filter by requested type
    articles = NewsArticle.objects.order_by("-published_at")[:100] if f in ("all", "articles") else []
    videos   = Video.objects.order_by("-published_at")[:100]       if f in ("all", "videos")   else []

    combined = []
    for item in articles:
        item.content_type = "article"
        item.normalized_published_at = normalize_date(item)
        combined.append(item)

    for item in videos:
        item.content_type = "video"
        item.normalized_published_at = normalize_date(item)
        combined.append(item)

    # Sort by normalized date desc, then cap to 100 items total
    top_100 = sorted(combined, key=lambda obj: obj.normalized_published_at, reverse=True)[:100]

    paginator = Paginator(top_100, 10)
    page_obj = paginator.get_page(page_number)

    return render(request, "news/news_list.html", {
        "page_obj": page_obj,
        "filter": f,
        "counts": counts,
    })
