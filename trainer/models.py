from django.db import models
from accounts.models import TraineeProfile
from jobs.models import Job
from django.conf import settings

class CandidateRecommendation(models.Model):
    trainee = models.ForeignKey(TraineeProfile, on_delete=models.CASCADE, related_name='placement_recommendations')
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='placement_recommendations')
    recommended_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    comments = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('trainee', 'job')

    def __str__(self):
        return f"{self.trainee} recommended for {self.job}"
