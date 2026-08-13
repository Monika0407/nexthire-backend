# notifications/views.py
"""
Notifications controller views.
Provides endpoints for dismissed lists or multi-read status resets.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Notification

@login_required
def mark_all_as_read_view(req):
    """
    Sets is_read state to true across all logged notifications of verified session.
    """
    req.user.notifications.filter(is_read=False).update(is_read=True)
    return redirect(req.META.get('HTTP_REFERER', 'accounts:role_routing'))

@login_required
def mark_single_as_read_view(req, alert_id):
    """
    Transitions a single in-app message.
    """
    alert = get_object_or_404(Notification, id=alert_id, user=req.user)
    alert.is_read = True
    alert.save()
    return redirect(req.META.get('HTTP_REFERER', 'accounts:role_routing'))


@login_required
def list_notifications_view(req):
    """
    Renders a dedicated notifications page for the logged-in user.
    """
    all_notifications = req.user.notifications.all().order_by('-created_at')
    # Mark all as read when they view this dedicated tab/page
    req.user.notifications.filter(is_read=False).update(is_read=True)
    return render(req, 'notifications/list.html', {
        'all_notifications': all_notifications
    })
