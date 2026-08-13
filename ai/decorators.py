# django_backend/ai/decorators.py
"""
Custom Role-Based Access Control (RBAC) Gating Decorators for NextHire AI Suite.
Terminates execution and redirects with error messages when unauthorized roles access specialized views.
"""

from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect
from accounts.models import Role

def student_required(view_func):
    """
    Blocks views unless logged in user profile role resolves to 'STUDENT'.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login') # assuming accounts:login exists
        
        try:
            profile = request.user.profile
            if profile.role == Role.TRAINEE:
                # Also assert they actually possess a TraineeProfile
                if hasattr(request.user, 'trainee_profile'):
                    return view_func(request, *args, **kwargs)
                else:
                    messages.warning(request, "Awaiting college registry setup. Please complete your trainee profile.")
                    return redirect('trainees:edit_profile')
        except Exception:
            pass
        
        messages.error(request, "HTTP 403 Forbidden. This AI module is restricted to trainee candidate accounts.")
        return redirect('trainees:dashboard' if hasattr(request.user, 'trainee_profile') else 'recruiters:dashboard')
    return _wrapped_view


def recruiter_required(view_func):
    """
    Blocks views unless user profile role resolves to 'RECRUITER'.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        
        try:
            profile = request.user.profile
            if profile.role == Role.RECRUITER:
                return view_func(request, *args, **kwargs)
        except Exception:
            pass
        
        messages.error(request, "HTTP 403 Forbidden. Recruiter corporate clearance is required to view these details.")
        return redirect('trainees:dashboard' if hasattr(request.user, 'trainee_profile') else 'recruiters:dashboard')
    return _wrapped_view


def admin_required(view_func):
    """
    Blocks views unless user profile role resolves to 'ADMIN' or is superuser.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
            
        try:
            profile = request.user.profile
            if profile.role == Role.ADMIN:
                return view_func(request, *args, **kwargs)
        except Exception:
            pass
        
        messages.error(request, "HTTP 403 Forbidden. Administrative clearance required for prompt management panels.")
        return redirect('trainees:dashboard' if hasattr(request.user, 'trainee_profile') else 'recruiters:dashboard')
    return _wrapped_view
