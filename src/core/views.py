from django.shortcuts import render
from disclosure.models import DisclosureEvent
from history.models import TimelineEvent
from news.models import NewsArticle
from evidence.models import EvidenceItem
from secrecy.models import SecrecyCase
from consciousness.models import Concept

def home(request):
    return render(request, "home.html", {
        "disclosures": DisclosureEvent.objects.all()[:5],
        "news": NewsArticle.objects.all()[:5],
        "history": TimelineEvent.objects.all()[:5],
    })

def disclosure_list(request):
    return render(request, "disclosure_list.html", {
        "disclosures": DisclosureEvent.objects.all(),
    })

def history_list(request):
    return render(request, "history_list.html", {
        "history": TimelineEvent.objects.all(),
    })

def news_list(request):
    return render(request, "news_list.html", {
        "news": NewsArticle.objects.all(),
    })

def evidence_list(request):
    return render(request, "evidence_list.html", {
        "evidence": EvidenceItem.objects.all(),
    })

def secrecy_list(request):
    return render(request, "secrecy_list.html", {
        "secrecy": SecrecyCase.objects.all(),
    })

def consciousness_list(request):
    return render(request, "consciousness_list.html", {
        "consciousness": Concept.objects.all
    })