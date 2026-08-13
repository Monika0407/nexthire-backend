# recruiters/urls.py
"""
Corporate recruitment partner route declarations.
Handles endpoints for corporate profiles, job postings CRUD management, 
pipelines review checklists, and interview coordinators.
"""

from django.urls import path
from . import views

app_name = 'recruiters'

urlpatterns = [
    # Dashboards Desk
    path('dashboard/', views.recruiter_dashboard_view, name='dashboard'),
    path('analytics/', views.recruiter_analytics_view, name='analytics'),
    
    # Company Profile Details
    path('profile/', views.edit_company_profile_view, name='profile'),
    path('company-profile/edit/', views.edit_company_profile_view, name='edit_profile'),
    
    # Vacant Positions CRUD controllers
    path('jobs/', views.recruiter_jobs_list_view, name='jobs'),
    path('jobs/create/', views.job_create_view, name='job_create'),
    path('jobs/edit/<int:job_id>/', views.job_edit_view, name='job_edit'),
    path('jobs/delete/<int:job_id>/', views.job_delete_view, name='job_delete'),
    path('jobs/toggle/<int:job_id>/', views.job_status_toggle_view, name='job_toggle'),
    
    # Legacy CRUD aliases
    path('job/new/', views.job_create_view, name='job_create_legacy'),
    path('job/edit/<int:job_id>/', views.job_edit_view, name='job_edit_legacy'),
    path('job/delete/<int:job_id>/', views.job_delete_view, name='job_delete_legacy'),
    path('job/toggle/<int:job_id>/', views.job_status_toggle_view, name='job_toggle_legacy'),
    
    # Candidates screenings & shortlistings
    path('applicants/', views.view_applicants_view, name='applicants'),
    path('applicants/list/', views.view_applicants_view, name='view_applicants'),
    path('applicants/<int:job_id>/', views.view_applicants_view, name='view_applicants_by_job'),
    path('application/status/<int:app_id>/<str:next_status>/', views.update_application_status_view, name='update_status'),
    path('application/schedule/<int:app_id>/', views.schedule_interview_view, name='schedule_interview'),
]
