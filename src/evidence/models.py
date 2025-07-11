from django.db import models

class EvidenceItem(models.Model):
    EVIDENCE_TYPE_CHOICES = [
        ('material', 'Material Sample'),
        ('biological', 'Biological Sample'),
        ('sensor', 'Sensor Footage'),
        ('image', 'Image/Photo'),
        ('other', 'Other'),
    ]

    title = models.CharField(max_length=300)
    description = models.TextField()
    evidence_type = models.CharField(max_length=50, choices=EVIDENCE_TYPE_CHOICES, default='other')
    date_observed = models.DateField(null=True, blank=True)
    origin = models.CharField(max_length=255, blank=True)
    url = models.URLField(blank=True)

    def __str__(self):
        return self.title
