# django_backend/ai/urls.py
"""
AI Suite URL Router config.
Isolates sub-pathways for resume diagnostic models, mock interviews,
conversational virtual coaches, and dynamic administrative prompt templates.
"""

from django.urls import path
from . import views

app_name = 'ai'

urlpatterns = [
    # General Hub & Analytics Summary
    path('', views.ai_dashboard, name='dashboard'),
    
    # Phase 2: Resume intelligence
    path('resume/analyze/', views.resume_analyze, name='resume_analyze'),
    
    # Phase 5: Resume improvement blueprints and progress
    path('resume/roadmap/', views.resume_roadmap, name='resume_roadmap'),
    path('resume/roadmap/progress/', views.update_roadmap_progress, name='update_roadmap_progress'),
    
    # Phase 3: AI Mock Interviews list and start
    path('interview/', views.interview_list, name='interview_list'),
    path('interview/start/', views.interview_start, name='interview_start'),
    path('interview/session/<int:session_id>/', views.interview_session, name='interview_session'),
    
    # Phase 4: Virtual Counselor interactive Chat interface
    path('guidance/', views.career_guidance, name='career_guidance'),
    path('guidance/send/', views.career_guidance_send, name='career_guidance_send'),
    
    # Phase 7: Dynamic administrative prompt parameters control panel
    path('prompts/', views.prompt_list, name='prompt_list'),
    path('prompts/<int:prompt_id>/edit/', views.prompt_edit, name='prompt_edit'),
]
