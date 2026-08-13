# students/urls.py
"""
Student Module routing matrix.
Configures paths for dashboards, profile config settings, resume management, and analytical metrics.
"""

from django.urls import path
from . import views

app_name = 'students'

urlpatterns = [
    # General Control Desk
    path('dashboard/', views.trainee_dashboard_view, name='dashboard'),
    
    # Profile & Academic Records
    path('profile/', views.trainee_profile_edit_view, name='profile'),
    path('profile/edit/', views.trainee_profile_edit_view, name='edit_profile'),
    path('course/', views.trainee_course_details_view, name='course_details'),
    path('course/request_edit/', views.trainee_course_request_edit_view, name='course_request_edit'),
    
    # Document Vault / Resumes
    path('resume/', views.resume_management_view, name='resume'),
    path('resume_management/', views.resume_management_view, name='resume_management'),
    path('resume/delete/', views.resume_delete_view, name='resume_delete'),
    path('resume/preview/<str:usn>/', views.resume_preview_view, name='resume_preview'),
    
    # Analytics & AI Intelligence Suite
    path('analytics/', views.trainee_analytics_view, name='analytics'),
    path('prediction/', views.trainee_prediction_view, name='prediction'),
    path('resume-analysis/', views.student_resume_analysis_view, name='resume_analysis'),
    path('interview/', views.student_interview_view, name='interview'),
    path('chatbot/', views.student_chatbot_view, name='chatbot'),
]

