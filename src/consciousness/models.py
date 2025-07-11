from django.db import models

class Concept(models.Model):
    title = models.CharField(max_length=255)
    summary = models.TextField()
    description = models.TextField()
    source_links = models.TextField(blank=True, help_text="Newline-separated URLs")
    tags = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.title
