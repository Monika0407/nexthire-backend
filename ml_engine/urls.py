# django_backend/ml_engine/urls.py
"""
Machine Learning Engine app-level URL Router coordinates.
"""

from django.urls import path
from . import views

app_name = 'ml_engine'

urlpatterns = [
    # Master ML Hub
    path('dashboard/', views.ml_dashboard_view, name='dashboard'),
    
    # Students microservices
    path('predict/', views.predict_placement_view, name='predict'),
    path('recommendations/', views.job_recommendation_view, name='recommendations'),
    path('skill-gap/', views.skill_gap_analysis_view, name='skill_gap'),
    
    # Recruiters rankings
    path('ranking/', views.candidate_ranking_view, name='ranking'),
    
    # Admins datasets and versioning
    path('datasets/', views.dataset_management_view, name='dataset_list'),
    path('retrain/', views.trigger_retrain_view, name='trigger_retrain'),
    path('retrain/<int:dataset_id>/', views.trigger_retrain_view, name='trigger_retrain_custom'),
    path('activate/<int:version_id>/', views.activate_model_version_view, name='activate_version'),
]
