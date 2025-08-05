from django.contrib import admin
from django.urls import path, include
from core import views as core_views
from news import views as news_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", core_views.home, name="home"),
    path("news/", news_views.news_list, name="news_list"),
]
