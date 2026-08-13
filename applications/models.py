# applications/models.py
"""
Job Applications database module.
Binds candidate students to active job vacancies with status tracking and screening scores.
Also supports Phase 7 Offer Letters and Release pipelines.
"""

from django.db import models
from accounts.models import StudentProfile
from jobs.models import Job
from recruiters.models import RecruiterProfile

class Status(models.TextChoices):
    PENDING = 'PENDING', 'Applied'
    SHORTLISTED = 'SHORTLISTED', 'Shortlisted'
    TESTING = 'TESTING', 'Online Assessment Stage'
    INTERVIEWING = 'INTERVIEWING', 'Interview Scheduled'
    OFFER_EXTENDED = 'OFFER_EXTENDED', 'Selected'
    OFFER_ACCEPTED = 'OFFER_ACCEPTED', 'Selected'
    REJECTED = 'REJECTED', 'Rejected'

class Application(models.Model):
    trainee = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='applications')
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='applications')
    resume = models.ForeignKey('trainees.Resume', on_delete=models.SET_NULL, blank=True, null=True, related_name='applications')
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.PENDING)
    applied_at = models.DateTimeField(auto_now_add=True)
    screener_score = models.IntegerField(default=60, help_text="AI-estimated skills screening rank score out of 100")
    feedback_notes = models.TextField(blank=True, null=True, help_text="Notes from corporate recruiter audit")

    class Meta:
        unique_together = ('trainee', 'job')
        ordering = ['-applied_at']

    def __str__(self):
        return f"{self.trainee.user.email} -> {self.job.title} ({self.status})"


class OfferStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending Decision'
    ACCEPTED = 'ACCEPTED', 'Offer Accepted'
    REJECTED = 'REJECTED', 'Offer Rejected'


class Offer(models.Model):
    """
    Phase 7 Offer Letter Register.
    Tracks letter distributions, packages, and statuses (Pending, Accepted, Rejected).
    """
    trainee = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='offers')
    company = models.ForeignKey(RecruiterProfile, on_delete=models.CASCADE, related_name='offers')
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='offers')
    package = models.CharField(max_length=50, help_text="e.g. 12 LPA")
    status = models.CharField(max_length=20, choices=OfferStatus.choices, default=OfferStatus.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    offer_letter_text = models.TextField(
        default="Dear candidate, We are pleased to extend this placement selection offer letter for the selected role parameters. Welcome aboard!", 
        help_text="Full contents of selection offer letter"
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Offer from {self.company.company_name} to {self.trainee.user.email} for {self.job.title} ({self.status})"
