# admin_custom/urls.py
"""
Platform Administration custom URLs matrix.
"""

from django.urls import path
from . import views

app_name = 'admin_custom'

urlpatterns = [
    path('dashboard/', views.admin_dashboard_view, name='dashboard'),
    path('analytics/', views.admin_analytics_view, name='analytics'),
    path('trainees/', views.admin_students_view, name='trainees'),
    path('recruiters/', views.admin_recruiters_view, name='recruiters'),
    path('trainers/', views.admin_officers_view, name='trainers'),
    path('jobs/', views.admin_jobs_view, name='jobs'),
    path('applications/', views.admin_applications_view, name='applications'),
]
