# jobs/urls.py
"""
Job listings URLs directory.
Exposes feeds and publishing paths.
"""

from django.urls import path
from . import views

app_name = 'jobs'

urlpatterns = [
    path('feed/', views.active_jobs_feed_view, name='feed'),
    path('publish/', views.post_new_job_view, name='publish'),
]
