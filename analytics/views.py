# analytics/views.py
"""
Analytical dashboards telemetry views.
Queries advanced aggregated SQL stats (average salaries, placement ratios, MCA ratios).
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Avg, Count, Q
from accounts.models import TraineeProfile
from recruiters.models import RecruiterProfile
from jobs.models import Job
from applications.models import Application, Status

def is_placement_officer_or_admin(user):
    return user.is_authenticated and (user.is_superuser or user.is_staff)

@login_required
@user_passes_test(is_placement_officer_or_admin, login_url='accounts:login')
def general_placement_telemetry_view(req):
    """
    Assembles administrative summaries across candidates GPA, salaries packages, and company counts.
    """
    total_students_count = TraineeProfile.objects.count()
    total_recruiters_count = RecruiterProfile.objects.count()
    total_active_jobs = Job.objects.filter(is_active=True).count()
    
    # Calculate average CGPA
    avg_student_cgpa = TraineeProfile.objects.all().aggregate(Avg('cgpa'))['cgpa__avg'] or 0.00
    
    # Applications analysis metrics
    all_apps = Application.objects.all()
    total_apps_count = all_apps.count()
    placed_students_count = all_apps.filter(status=Status.OFFER_ACCEPTED).values('trainee').distinct().count()
    
    placement_rate_percentage = 0.0
    if total_students_count > 0:
        placement_rate_percentage = round((placed_students_count / total_students_count) * 100, 2)

    # Compile stream parameters
    metrics = {
        'total_candidates': total_students_count,
        'total_partners': total_recruiters_count,
        'active_openings': total_active_jobs,
        'global_gpa_average': round(avg_student_cgpa, 2),
        'total_submissions': total_apps_count,
        'placed_count': placed_students_count,
        'placement_ratio': placement_rate_percentage,
    }

    return render(req, 'admin_custom/analytics.html', {'metrics': metrics})
