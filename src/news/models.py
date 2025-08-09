from django.db import models

class NewsSource(models.Model):
    name = models.CharField(max_length=255)
    url = models.URLField(blank=True)

    def __str__(self):
        return self.name


class NewsArticle(models.Model):
    title = models.CharField(max_length=500)
    summary = models.TextField()
    source = models.ForeignKey(NewsSource, on_delete=models.SET_NULL, null=True, blank=True)
    url = models.URLField()
    published_at = models.DateField()
    tags = models.CharField(max_length=255, blank=True)
    raw_data = models.JSONField(blank=True, null=True)

    class Meta:
        ordering = ['-published_at']

    def __str__(self):
        return self.title


class VideoSource(models.Model):
    name = models.CharField(max_length=255)
    channel_id = models.CharField(max_length=100, unique=True)
    last_fetched_at = models.DateTimeField(null=True, blank=True) 

    def __str__(self):
        return self.name


class Video(models.Model):
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    url = models.URLField(unique=True)
    published_at = models.DateTimeField()
    source = models.ForeignKey(VideoSource, on_delete=models.SET_NULL, null=True, blank=True)
    raw_data = models.JSONField(blank=True, null=True)

    class Meta:
        ordering = ['-published_at']

    def __str__(self):
        return self.title


class IngestionStatus(models.Model):
    # Singleton row with fixed PK = 1
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    last_run_started = models.DateTimeField(null=True, blank=True)
    last_success_any = models.DateTimeField(null=True, blank=True)          # task succeeded (even if 0 new)
    last_success_with_new = models.DateTimeField(null=True, blank=True)     # succeeded AND added new items
    last_error = models.TextField(null=True, blank=True)

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj