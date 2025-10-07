# news/admin.py
from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.db.models import JSONField
from django.contrib.admin.widgets import AdminJSONEditor

from .models import (
    NewsSource,
    NewsArticle,
    VideoSource,
    Video,
    IngestionStatus,
)

# ---------- Inline/Widgets ----------
JSON_OVERRIDES = {
    JSONField: {"widget": AdminJSONEditor},
}

# ---------- News ----------
@admin.register(NewsSource)
class NewsSourceAdmin(admin.ModelAdmin):
    list_display = ("name", "url")
    search_fields = ("name", "url")
    ordering = ("name",)


@admin.register(NewsArticle)
class NewsArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "source", "published_at")
    list_filter = ("source", "published_at")
    search_fields = ("title", "summary", "url")
    date_hierarchy = "published_at"
    ordering = ("-published_at", "title")
    autocomplete_fields = ("source",)
    formfield_overrides = JSON_OVERRIDES


# ---------- Video ----------
@admin.register(VideoSource)
class VideoSourceAdmin(admin.ModelAdmin):
    list_display = ("name", "channel_id", "last_fetched_at")
    search_fields = ("name", "channel_id")
    ordering = ("name",)
    readonly_fields = ("last_fetched_at",)


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ("title", "channel_title_display", "published_at", "url")
    list_filter = ("source", "published_at")
    search_fields = ("title", "description", "url")
    date_hierarchy = "published_at"
    ordering = ("-published_at", "title")
    autocomplete_fields = ("source",)
    formfield_overrides = JSON_OVERRIDES
    readonly_fields = ("video_id_display",)

    @admin.display(description="Channel")
    def channel_title_display(self, obj):
        return obj.channel_title

    @admin.display(description="Video ID")
    def video_id_display(self, obj):
        return obj.video_id


# ---------- IngestionStatus (singleton) ----------
@admin.register(IngestionStatus)
class IngestionStatusAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "last_run_started",
        "last_success_any",
        "last_success_with_new",
        "short_last_error",
    )
    readonly_fields = ("id",)
    formfield_overrides = JSON_OVERRIDES
    ordering = ("id",)

    def has_add_permission(self, request):
        # Prevent creating extra rows
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        # Redirect list → the single object’s change page (pk=1)
        obj, _ = IngestionStatus.objects.get_or_create(pk=1)
        url = reverse("admin:news_ingestionstatus_change", args=(obj.pk,))
        return HttpResponseRedirect(url)

    @admin.display(description="Last error (truncated)")
    def short_last_error(self, obj):
        if not obj.last_error:
            return ""
        s = str(obj.last_error)
        return s if len(s) <= 100 else s[:100] + "…"
