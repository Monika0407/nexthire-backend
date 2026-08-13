# interviews/urls.py
"""
Interview Scheduling and Evaluation URIs directory mapping.
Channels scheduling forms, evaluations directories, and calendars.
"""

from django.urls import path
from . import views

app_name = 'interviews'

urlpatterns = [
    # Dashboards (Phase 6)
    path('dashboard/trainee/', views.student_interview_dashboard_view, name='student_dashboard'),
    path('dashboard/recruiter/', views.recruiter_interview_dashboard_view, name='recruiter_dashboard'),

    # Actions & Forms (Phase 4 & 5)
    path('schedule/<int:app_id>/', views.schedule_interview_view, name='schedule'),
    path('evaluate/<int:interview_id>/', views.evaluate_interview_view, name='evaluate'),
    path('cancel/<int:interview_id>/', views.cancel_interview_view, name='cancel'),
]
