from django.shortcuts import render
from disclosure.models import DisclosureEvent
from history.models import TimelineEvent
from news.models import NewsArticle
from evidence.models import EvidenceItem
from secrecy.models import SecrecyCase
from consciousness.models import Concept

def home(request):
    return render(request, "core/home.html", {
        "disclosures": DisclosureEvent.objects.all()[:5],
        "news": NewsArticle.objects.all()[:5],
        "history": TimelineEvent.objects.all()[:5],
    })