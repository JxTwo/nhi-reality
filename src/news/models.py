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
