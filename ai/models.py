# django_backend/ai/models.py
"""
AI Engine Database Schema definitions.
Tracks prompt templates, resume evaluation readiness metrics, mock interview sequences, 
and professional career guidance chat logs.
"""

from django.db import models
from accounts.models import TraineeProfile
from jobs.models import Job

class PromptTemplate(models.Model):
    """
    Saves and tracks versions of prompt instructions sent to Gemini API.
    Enables immediate runtime updates to system and user prompts without code redeployments.
    """
    name = models.CharField(max_length=100, unique=True, help_text="Unique prompt moniker e.g., 'resume_analysis'")
    system_instruction = models.TextField(help_text="The core instruction that defines behavioral bounds for the AI safety and roleplay context.")
    user_template = models.TextField(help_text="Standard prompt template interpolating variables like {resume_text} or {job_skills}.")
    version = models.IntegerField(default=1, help_text="Incremented version marker for systemic performance auditing.")
    is_active = models.BooleanField(default=True, help_text="Controls if this prompt template is used at runtime.")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.name} (v{self.version})"


class ResumeAnalysis(models.Model):
    """
    Stores metrics, summarization text, and technical items mapped from uploaded PDF/Doc resumes.
    """
    trainee = models.ForeignKey(TraineeProfile, on_delete=models.CASCADE, related_name='resume_analyses')
    resume_score = models.IntegerField(default=0, help_text="AI estimated overall placement compatibility score out of 100")
    resume_summary = models.TextField(blank=True, null=True, help_text="Brief professional summary extracted from the resume contents")
    missing_skills = models.JSONField(default=list, help_text="List of recommended high-value technical skills candidates lack")
    improvement_tips = models.JSONField(default=list, help_text="Step-by-step suggestions for candidate styling, wording, or projects modifications")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Resume Analyses"

    def __str__(self):
        return f"Resume Evaluation for {self.trainee.user.email} - Score: {self.resume_score}%"


class ResumeRoadmap(models.Model):
    """
    Actionable progress-tracking entities targeting resume enhancement.
    """
    trainee = models.ForeignKey(TraineeProfile, on_delete=models.CASCADE, related_name='resume_roadmaps')
    weak_areas = models.JSONField(default=list, help_text="Weak points identified in the resume (e.g. 'Lack of Docker deployment')")
    recommendations = models.JSONField(default=list, help_text="Action items or specific courses / certifications to bridge the gaps")
    target_resume_suggestions = models.TextField(help_text="A customized blueprint / outline of what their enhanced resume should read like")
    progress_percentage = models.IntegerField(default=0, help_text="Candidate progress in ticking off these recommendations")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Enhancement Blueprint for {self.trainee.user.email} - {self.progress_percentage}% Compiled"


class InterviewSession(models.Model):
    """
    Represents an ongoing or completed AI role-specific mock interview workspace.
    """
    trainee = models.ForeignKey(TraineeProfile, on_delete=models.CASCADE, related_name='interview_sessions')
    job = models.ForeignKey(Job, on_delete=models.SET_NULL, null=True, blank=True, related_name='mock_interviews')
    role_title = models.CharField(max_length=150, help_text="The target technical position e.g., 'Cloud Infrastructure Engineer'")
    current_question_index = models.IntegerField(default=0, help_text="Dynamic counter representing current phase (max 5 questions usually)")
    technical_score = models.IntegerField(default=0, help_text="Calculated performance indicator for domain compliance out of 100")
    communication_score = models.IntegerField(default=0, help_text="Calculated presentation and behavioral index score out of 100")
    suggestions = models.TextField(blank=True, null=True, help_text="Actionable constructive evaluation summary compiled post interview")
    is_completed = models.BooleanField(default=False, help_text="True if evaluation algorithms verified last answer stream")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.role_title} Practice Session for {self.trainee.user.email} (Completed: {self.is_completed})"


class InterviewMessage(models.Model):
    """
    Logs single exchange turns in a corporate technical mock mock interview.
    """
    session = models.ForeignKey(InterviewSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=15, choices=[('ai', 'AI Host'), ('trainee', 'Candidate Student')])
    content = models.TextField()
    feedback = models.JSONField(default=dict, blank=True, help_text="Mini score and tip for trainee's individual response if role='trainee'")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Msg {self.id} for {self.session.id} ({self.role})"


class CareerGuidanceSession(models.Model):
    """
    An individual session for trainee career guidance chat support.
    """
    trainee = models.ForeignKey(TraineeProfile, on_delete=models.CASCADE, related_name='career_sessions')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Career Guidance for {self.trainee.user.email} at {self.created_at.strftime('%Y-%m-%d')}"


class CareerGuidanceMessage(models.Model):
    """
    Detailed conversational record of a Career Guidance session.
    """
    session = models.ForeignKey(CareerGuidanceSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=15, choices=[('user', 'Student User'), ('ai', 'AI Counselor')])
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Chat Msg for Session {self.session_id} - {self.role.upper()}"
