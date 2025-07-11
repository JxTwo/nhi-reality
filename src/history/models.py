from django.db import models

class TimelineEvent(models.Model):
    title = models.CharField(max_length=300)
    date = models.DateField()
    description = models.TextField()
    is_uap_related = models.BooleanField(default=True)
    source_link = models.URLField(blank=True)
    tags = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['date']

    def __str__(self):
        return f"{self.title} ({self.date})"
