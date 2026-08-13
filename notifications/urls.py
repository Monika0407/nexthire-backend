# notifications/urls.py
"""
URL directory paths for real-time notification dismissing.
"""

from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.list_notifications_view, name='list'),
    path('mark-all-read/', views.mark_all_as_read_view, name='mark_all_read'),
    path('mark-read/<int:alert_id>/', views.mark_single_as_read_view, name='mark_single_read'),
]
