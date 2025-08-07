from django.core.paginator import Paginator
from django.shortcuts import render
from news.models import NewsArticle, Video
from core.utilities import normalize_date


def news_list(request):
    # Fetch up to 100 of each type
    articles = NewsArticle.objects.order_by("-published_at")[:100]
    videos = Video.objects.order_by("-published_at")[:100]

    # Merge and annotate with type + normalized date
    combined = []

    for item in articles:
        item.content_type = "article"
        item.normalized_published_at = normalize_date(item)
        combined.append(item)

    for item in videos:
        item.content_type = "video"
        item.normalized_published_at = normalize_date(item)
        combined.append(item)

    # Sort all by normalized date (desc) and slice top 100
    top_100 = sorted(combined, key=lambda obj: obj.normalized_published_at, reverse=True)[:100]

    # Paginate
    paginator = Paginator(top_100, 10)  # 10 per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "news/news_list.html", {
        "page_obj": page_obj
    })
