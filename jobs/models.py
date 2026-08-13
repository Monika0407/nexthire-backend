# jobs/models.py
"""
Job postings database representation.
Ties back to recruiter profiles, enforces eligibility threshold constraints.
"""

from django.db import models
from recruiters.models import RecruiterProfile

class Job(models.Model):
    class JobType(models.TextChoices):
        FULL_TIME = 'FULL_TIME', 'Full-time Employment'
        INTERNSHIP = 'INTERNSHIP', 'Corporate Internship'
        CONTRACT = 'CONTRACT', 'Freelance / Contract'

    recruiter = models.ForeignKey(RecruiterProfile, on_delete=models.CASCADE, related_name='jobs')
    title = models.CharField(max_length=150, verbose_name="Job Role Title")
    description = models.TextField(help_text="Detailed description of roles and technical responsibilities")
    job_type = models.CharField(max_length=20, choices=JobType.choices, default=JobType.FULL_TIME)
    location = models.CharField(max_length=100, default="Bengaluru, IND")
    salary_package =models.CharField(max_length=50, help_text="Estimated annual CTC (e.g. 12 LPA) or monthly stipend")
    skills_required = models.JSONField(default=list, help_text="JSON list of mandatory skills required")
    required_courses = models.ManyToManyField('accounts.Course', blank=True, related_name='jobs')
    min_cgpa_required = models.DecimalField(
        max_digits=4, 
        decimal_places=2, 
        default=6.00, 
        help_text="Minimum threshold CGPA score to submit application"
    )
    experience_required = models.IntegerField(
        default=0,
        blank=True,
        help_text="Minimum years of experience required for this job"
    )
    is_active = models.BooleanField(default=True, help_text="Controls visibility in active trainee trainee feeds")
    posted_at = models.DateTimeField(auto_now_add=True)
    application_deadline = models.DateField()

    def __str__(self):
        return f"{self.title} @ {self.recruiter.company_name}"

    @property
    def eligibility(self):
        return self.min_cgpa_required

    @eligibility.setter
    def eligibility(self, value):
        self.min_cgpa_required = value

    @property
    def salary(self):
        return self.salary_package

    @salary.setter
    def salary(self, value):
        self.salary_package = value

    @property
    def deadline(self):
        return self.application_deadline

    @deadline.setter
    def deadline(self, value):
        self.application_deadline = value

    @property
    def status(self):
        return 'Open' if self.is_active else 'Closed'

    @status.setter
    def status(self, value):
        self.is_active = (value == 'Open')
