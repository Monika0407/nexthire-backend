# notifications/context_processors.py
from notifications.models import Notification
from accounts.models import TraineeProfile, RecruiterProfile, TrainerProfile

def notifications(request):
    if request.user.is_authenticated:
        unread_notifications = request.user.notifications.filter(is_read=False).order_by('-created_at')[:5]
        unread_count = request.user.notifications.filter(is_read=False).count()
        
        # Pending counts for admin and placement trainer dashboards
        pending_students_count = TraineeProfile.objects.filter(approval_status='pending').count()
        pending_recruiters_count = RecruiterProfile.objects.filter(is_approved_by_admin=False).count()
        pending_officers_count = TrainerProfile.objects.filter(is_approved=False).count()
        
        # Count unread job alerts for trainee feed badge
        unread_job_alerts_count = request.user.notifications.filter(notification_type='JOB_ALERT', is_read=False).count()
        
        return {
            'unread_notifications': unread_notifications,
            'unread_notifications_count': unread_count,
            'unread_job_alerts_count': unread_job_alerts_count,
            'pending_students_count': pending_students_count,
            'pending_recruiters_count': pending_recruiters_count,
            'pending_officers_count': pending_officers_count,
        }
    return {
        'unread_notifications': [],
        'unread_notifications_count': 0,
        'unread_job_alerts_count': 0,
        'pending_students_count': 0,
        'pending_recruiters_count': 0,
        'pending_officers_count': 0,
    }
