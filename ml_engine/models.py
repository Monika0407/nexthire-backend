# django_backend/ml_engine/models.py
"""
Machine Learning Engine Models definition.
Tracks training datasets, model versions metadata, prediction audits, and cached recommendations.
"""

from django.db import models
from accounts.models import TraineeProfile
from jobs.models import Job

class MLModelMetadata(models.Model):
    """
    Metadata registry for trained models, version tracking, and performance logs in MySQL.
    """
    version = models.CharField(max_length=50, unique=True, help_text="Model version identifier (e.g. v2026.06.11)")
    algorithm_name = models.CharField(max_length=150, default="RandomForestClassifier")
    accuracy = models.FloatField(help_text="Model overall accuracy score")
    precision = models.FloatField(help_text="Model precision score")
    recall = models.FloatField(help_text="Model recall score")
    f1_score = models.FloatField(help_text="Model F1 score parameter")
    
    # Path inside filesystem
    model_file_path = models.CharField(max_length=500, help_text="Absolute or relative path to joblib serialized file")
    scaler_file_path = models.CharField(max_length=500, blank=True, null=True, help_text="Path to scaler joblib file if used")
    features_used = models.JSONField(default=list, help_text="List of feature names input into the model")
    
    # Active model state
    is_active = models.BooleanField(default=False, help_text="Determines if this version is queried on production endpoints")
    
    trained_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True, null=True, help_text="Voluntary summary notes for model changes")

    class Meta:
        ordering = ['-trained_at']
        verbose_name = "ML Model Metadata"
        verbose_name_plural = "ML Model Metadata Logs"

    def __str__(self):
        status = "ACTIVE" if self.is_active else "INACTIVE"
        return f"Version {self.version} ({self.algorithm_name}) — Acc: {self.accuracy:.2%} [{status}]"

    @property
    def accuracy_percentage(self):
        return round(self.accuracy * 100, 1)


class TrainingDataset(models.Model):
    """
    Stores historical records of datasets used to feed the ML engine training loops.
    """
    name = models.CharField(max_length=250, help_text="Dataset registry label")
    file_upload = models.FileField(upload_to="ml_datasets/", blank=True, null=True, help_text="Optional CSV data source file")
    is_validated = models.BooleanField(default=False, help_text="Dataset structure and format check index")
    rows_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.rows_count} records) — {self.created_at.strftime('%Y-%m-%d')}"


class CandidatePlacementPrediction(models.Model):
    """
    Stores logs of individual predictions. Great of status tracking, auditing, and retraining feedbacks.
    """
    trainee = models.ForeignKey(TraineeProfile, on_delete=models.CASCADE, related_name="placement_predictions", null=True, blank=True)
    
    # Input attributes logged
    cgpa = models.FloatField()
    skills_count = models.IntegerField()
    internships_count = models.IntegerField()
    certifications_count = models.IntegerField()
    aptitude_score = models.IntegerField()
    projects_count = models.IntegerField()
    
    # Output variables logged
    placement_probability = models.FloatField(help_text="Calculated model placement probability (0.0 to 1.0)")
    confidence_score = models.FloatField(help_text="Accuracy confidence indices based on feature distribution")
    
    predicted_at = models.DateTimeField(auto_now_add=True)
    model_version = models.ForeignKey(MLModelMetadata, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['-predicted_at']

    @property
    def probability_percentage(self):
        return round(self.placement_probability * 100, 1)

    def __str__(self):
        name = self.trainee.user.get_full_name() if (self.trainee and self.trainee.user) else "Anonymous Student"
        return f"Prediction for {name} ({self.placement_probability:.1%})"


class JobRecommendationCache(models.Model):
    """
    Intermediary caching tables to save recommended job openings per student profile.
    """
    trainee = models.ForeignKey(TraineeProfile, on_delete=models.CASCADE, related_name="job_recommendations")
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    match_score = models.FloatField(help_text="Calculated matching coefficient (0 to 100)")
    matching_skills = models.JSONField(default=list)
    missing_skills = models.JSONField(default=list)
    cached_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('trainee', 'job')
        ordering = ['-match_score']

    def __str__(self):
        return f"Recommendation: {self.trainee} -> {self.job.title} ({self.match_score}%)"
