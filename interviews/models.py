# interviews/models.py
"""
Interview Scheduling database layout.
Links with specific applications. Tracks meet coordinates and corporate reviews.
"""

from django.db import models
from applications.models import Application

class Interview(models.Model):
    class Stage(models.TextChoices):
        TECHNICAL = 'TECHNICAL', 'Technical Evaluation Round'
        MANAGERIAL = 'MANAGERIAL', 'Managerial Assessment'
        HR = 'HR', 'Human Resources Culture Fit'

    class Status(models.TextChoices):
        SCHEDULED = 'SCHEDULED', 'Scheduled'
        COMPLETED = 'COMPLETED', 'Completed'
        SELECTED = 'SELECTED', 'Selected'
        REJECTED = 'REJECTED', 'Rejected'
        CANCELLED = 'CANCELLED', 'Cancelled'

    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='interviews')
    title = models.CharField(max_length=150, help_text="e.g. Technical Round 1")
    stage = models.CharField(max_length=30, choices=Stage.choices, default=Stage.TECHNICAL)
    scheduled_at = models.DateTimeField(help_text="Time coordinates for candidate slot")
    platform = models.CharField(max_length=50, default="Google Meet")
    meet_url = models.URLField(max_length=255, blank=True, null=True, verbose_name="Video Call URL link")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED)
    feedback_notes = models.TextField(blank=True, null=True, help_text="Detailed evaluation remarks and performance ratings")
    rating_score = models.IntegerField(blank=True, null=True, help_text="Candidate performance score (1-5)")

    class Meta:
        ordering = ['-scheduled_at']

    def __str__(self):
        return f"{self.title} - {self.application.trainee.user.email} @ {self.scheduled_at.strftime('%Y-%m-%d %H:%M')}"

    @property
    def candidate(self):
        return self.application.trainee

    @property
    def job(self):
        return self.application.job

    @property
    def date(self):
        return self.scheduled_at.date()

    @property
    def time(self):
        return self.scheduled_at.time()
