# notifications/models.py
"""
In-app and email notification architecture database mapping.
Ties event alerts to standard users for immediate alert synchronization.
"""

from django.db import models
from django.core.mail import send_mail
from django.conf import settings

class Notification(models.Model):
    class Type(models.TextChoices):
        JOB_ALERT = 'JOB_ALERT', 'New Active Job Post'
        STUDENT_APPLIED = 'STUDENT_APPLIED', 'Candidate Submitted Registration'
        INTERVIEW_INVITATION = 'INTERVIEW_INVITATION', 'Interview Invitation Scheduling'
        STATUS_UPDATE = 'STATUS_UPDATE', 'Application Pipeline Shift'
        ADMIN_BROADCAST = 'ADMIN_BROADCAST', 'General Campus Announcement'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=30, choices=Type.choices, default=Type.STATUS_UPDATE)
    is_read = models.BooleanField(default=False)
    redirect_url = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} | {self.title} ({'Read' if self.is_read else 'Unread'})"

    def dispatch_email(self):
        """
        SMTP dispatcher stub. Handles sending real-time transactional alert emails 
        such as interview invitations and status updates to candidates.
        """
        subject = f"[NextHire Alert] {self.title}"
        plain_message = self.message
        recipient_list = [self.user.email]
        
        try:
            # Under production, integrates Django standard SMTP triggers
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'alerts@nexthire.net'),
                recipient_list=recipient_list,
                fail_silently=False,
            )
            return True
        except Exception as e:
            # Gracefully log or handle email delivery delays without crashing transactions
            print(f"[SMTP Failure] Email delivery failed: {str(e)}")
            return False

    def get_action_url(self):
        """
        Determines the correct redirection page depending on the user role and notification content.
        """
        if self.redirect_url:
            return self.redirect_url
            
        from django.urls import reverse
        
        role = getattr(self.user.profile, 'role', None) if hasattr(self.user, 'profile') else None
        
        title_lower = self.title.lower()
        msg_lower = self.message.lower()

        if role == 'trainee':
            if 'interview' in title_lower or 'interview' in msg_lower:
                return reverse('interviews:student_dashboard')
            elif 'offer' in title_lower or 'offer' in msg_lower or 'select' in title_lower or 'select' in msg_lower or 'status' in title_lower or 'status' in msg_lower or 'pipeline' in title_lower or 'pipeline' in msg_lower:
                return reverse('applications:tracking')
            elif 'job' in title_lower or 'hiring' in title_lower or 'vacancy' in title_lower:
                return reverse('jobs:feed')
            elif 'profile' in title_lower or 'approved' in title_lower or 'rejected' in title_lower or 'verification' in title_lower:
                return reverse('trainees:profile')
            return reverse('trainees:dashboard')
            
        elif role == 'recruiter':
            if 'apply' in title_lower or 'applied' in title_lower or 'candidate' in title_lower or 'submittal' in title_lower or 'recommendation' in title_lower or 'recommended' in title_lower:
                return reverse('recruiters:applicants')
            elif 'interview' in title_lower or 'interview' in msg_lower:
                return reverse('interviews:recruiter_dashboard')
            return reverse('recruiters:dashboard')
            
        elif role == 'trainer':
            if 'recruiter' in title_lower or 'recruiter' in msg_lower:
                return reverse('trainer:recruiters')
            elif 'trainee' in title_lower or 'trainee' in msg_lower or 'register' in title_lower or 'register' in msg_lower or 'edit' in title_lower or 'edit' in msg_lower:
                return reverse('trainer:trainees')
            elif 'job' in title_lower or 'job' in msg_lower or 'vacancy' in title_lower or 'vacancy' in msg_lower:
                return reverse('trainer:trainees')
            return reverse('trainer:dashboard')
            
        elif role == 'admin' or self.user.is_superuser:
            if 'trainer' in title_lower or 'trainer' in msg_lower:
                return reverse('admin_custom:trainers')
            elif 'trainee' in title_lower or 'trainee' in msg_lower:
                return reverse('admin_custom:trainees')
            elif 'recruiter' in title_lower or 'recruiter' in msg_lower:
                return reverse('admin_custom:recruiters')
            elif 'job' in title_lower or 'job' in msg_lower:
                return reverse('admin_custom:jobs')
            return reverse('admin_custom:dashboard')

        try:
            return reverse('admin_custom:dashboard')
        except Exception:
            return '#'
