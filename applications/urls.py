# applications/urls.py
"""
Job tracking and Selection offer letter URIs directory mapping.
Channels submission transitions and letter registries.
"""

from django.urls import path
from . import views

app_name = 'applications'

urlpatterns = [
    # Application submissions
    path('apply/<int:job_id>/', views.apply_job_view, name='apply'),
    path('withdraw/<int:app_id>/', views.withdraw_application_view, name='withdraw'),
    path('tracking/', views.student_applications_tracking_view, name='tracking'),
    path('resume/<int:app_id>/', views.application_resume_preview_view, name='application_resume_preview'),
    path('update-status/<int:app_id>/', views.update_application_status_view, name='update_status'),
    
    # Offer Management (Phase 7 & 8)
    path('offer/generate/', views.generate_offer_view, name='offer_generate_base'),
    path('offer/generate/<int:app_id>/', views.generate_offer_view, name='offer_generate'),
    path('offer/accept/<int:offer_id>/', views.accept_offer_view, name='offer_accept'),
    path('offer/reject/<int:offer_id>/', views.reject_offer_view, name='offer_reject'),
    path('offer/download/<int:offer_id>/', views.download_offer_view, name='offer_download'),
]
