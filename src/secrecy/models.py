from django.db import models

class SecrecyCase(models.Model):
    title = models.CharField(max_length=300)
    description = models.TextField()
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    confirmed = models.BooleanField(default=False)
    source_link = models.URLField(blank=True)
    tags = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.title
