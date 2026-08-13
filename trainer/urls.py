from django.urls import path
from . import views

app_name = 'placement'

urlpatterns = [
    path('dashboard/', views.trainer_dashboard_view, name='dashboard'),
    path('analytics/', views.trainer_analytics_view, name='analytics'),
    path('update-courses/', views.trainer_update_courses_view, name='update_courses'),
    path('students/', views.trainer_trainees_view, name='students'),
    path('students/', views.trainer_trainees_view, name='trainees'),
    path('approve/', views.trainer_approve_view, name='approve'),
    path('recommend/', views.trainer_recommend_view, name='recommend'),
    path('recruiters/', views.trainer_recruiters_view, name='recruiters'),
    path('approve-recruiter/', views.trainer_approve_recruiter_view, name='approve_recruiter'),
    path('jobs/', views.trainer_jobs_view, name='jobs'),
]
