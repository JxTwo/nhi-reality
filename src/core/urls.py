from django.contrib import admin
from django.urls import path, include
from core import views as core_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", core_views.home, name="home"),
    path("disclosures/", core_views.disclosure_list, name="disclosure_list"),
    path("history/", core_views.history_list, name="history_list"),
    path("news/", core_views.news_list, name="news_list"),
    path("evidence/", core_views.evidence_list, name="evidence_list"),
    path("secrecy/", core_views.secrecy_list, name="secrecy_list"),
    path("consciousness/", core_views.consciousness_list, name="consciousness_list"),
]
