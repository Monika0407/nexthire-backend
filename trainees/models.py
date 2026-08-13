# trainees/models.py
from django.db import models
from accounts.models import TraineeProfile

class Resume(models.Model):
    trainee = models.ForeignKey(TraineeProfile, on_delete=models.CASCADE, related_name='resumes')
    resume_file = models.FileField(upload_to='student_resumes/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Resume for {self.trainee.user.email} (Uploaded: {self.uploaded_at})"
