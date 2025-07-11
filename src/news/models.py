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

    class Meta:
        ordering = ['-published_at']

    def __str__(self):
        return self.title
