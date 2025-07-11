from django.db import models


class DisclosureSource(models.Model):
    name = models.CharField(max_length=255)
    title = models.CharField(max_length=255, blank=True)
    affiliation = models.CharField(max_length=255, blank=True)
    bio = models.TextField(blank=True)

    is_government_official = models.BooleanField(default=False)
    is_military = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class DisclosureEvent(models.Model):
    EVENT_TYPE_CHOICES = [
        ("hearing", "Congressional Hearing"),
        ("interview", "Interview"),
        ("press", "Press Conference"),
        ("leak", "Leaked Testimony or Memo"),
        ("statement", "Public Statement"),
        ("article", "Published Article"),
        ("other", "Other"),
    ]

    title = models.CharField(max_length=300)
    date = models.DateField()
    source = models.ManyToManyField(DisclosureSource, related_name="events")
    description = models.TextField()

    event_type = models.CharField(
        max_length=30,
        choices=EVENT_TYPE_CHOICES,
        default="other"
    )

    source_link = models.URLField(
        blank=True,
        help_text="Link to article, transcript, or media"
    )

    tags = models.CharField(
        max_length=255,
        blank=True,
        help_text="Comma-separated list of tags (e.g., NHI, crash retrieval)"
    )

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.title} ({self.date})"


class DisclosureDocument(models.Model):
    event = models.ForeignKey(DisclosureEvent, on_delete=models.CASCADE, related_name="documents")
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to="documents/", blank=True)
    url = models.URLField(blank=True)

    def __str__(self):
        return self.title


class DisclosureClaim(models.Model):
    event = models.ForeignKey(DisclosureEvent, on_delete=models.CASCADE, related_name="claims")
    content = models.TextField()
    is_direct_quote = models.BooleanField(default=False)

    def __str__(self):
        return self.content[:80] + "..."
