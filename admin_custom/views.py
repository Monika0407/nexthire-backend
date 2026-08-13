# admin_custom/views.py
"""
Platform Administration custom views module.
Provides centralized dashboards control desk, Student management activation lanes, 
Recruiter verification workflows, Jobs modifications, Applications tracking pipelines, and Reports.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import models
from accounts.models import CustomUser, TraineeProfile, RecruiterProfile, TrainerProfile, Role
from jobs.models import Job
from recruiters.forms import JobForm
from applications.models import Application, Status
from interviews.models import Interview
from notifications.models import Notification

def is_admin(user):
    return user.is_authenticated and (user.role == 'admin' or user.is_superuser)

@login_required
@user_passes_test(is_admin, login_url='accounts:login_admin')
def admin_dashboard_view(req):
    """
    Renders custom admin panel showing platform-wide key metrics,
    recent logs activity streams, and basic reports views.
    """
    total_students = TraineeProfile.objects.count()
    total_recruiters = RecruiterProfile.objects.count()
    total_jobs = Job.objects.count()
    total_applications = Application.objects.count()
    total_interviews = Interview.objects.count()
    total_placements = Application.objects.filter(status='OFFER_ACCEPTED').count()

    recent_registrations = CustomUser.objects.all().order_by('-date_joined')[:5]
    recent_jobs = Job.objects.all().order_by('-posted_at')[:5]
    recent_applications = Application.objects.all().order_by('-applied_at')[:5]

    # Report Data Compilation
    student_report = TraineeProfile.objects.all().select_related('user').prefetch_related('courses')
    recruiter_report = RecruiterProfile.objects.all().select_related('user')
    placement_report = Application.objects.filter(status='OFFER_ACCEPTED').select_related(
        'trainee', 'trainee__user', 'job', 'job__recruiter'
    )
    job_report = Job.objects.all().select_related('recruiter').prefetch_related('required_courses')
    application_report = Application.objects.all().select_related('trainee', 'trainee__user', 'job', 'job__recruiter')

    tab = req.GET.get('tab', 'overview')

    context = {
        'total_students': total_students,
        'total_recruiters': total_recruiters,
        'total_jobs': total_jobs,
        'total_applications': total_applications,
        'total_interviews': total_interviews,
        'total_placements': total_placements,
        'recent_registrations': recent_registrations,
        'recent_jobs': recent_jobs,
        'recent_applications': recent_applications,
        'student_report': student_report,
        'recruiter_report': recruiter_report,
        'placement_report': placement_report,
        'job_report': job_report,
        'application_report': application_report,
        'active_tab': tab
    }
    return render(req, 'admin/dashboard.html', context)

@login_required
@user_passes_test(is_admin, login_url='accounts:login_admin')
def admin_students_view(req):
    """
    Administrate trainee profiles lists with search filters, detailed views, 
    and enable / disable account activation status options.
    """
    q = req.GET.get('q', '')
    if q:
        trainees = TraineeProfile.objects.filter(
            models.Q(user__email__icontains=q) | 
            models.Q(batch_code__icontains=q) |
            models.Q(user__first_name__icontains=q) |
            models.Q(user__last_name__icontains=q)
        ).select_related('user').prefetch_related('courses')
    else:
        trainees = TraineeProfile.objects.all().select_related('user').prefetch_related('courses')

    detail_student = None
    detail_id = req.GET.get('detail')
    if detail_id:
        detail_student = get_object_or_404(TraineeProfile, id=detail_id)

    if req.method == 'POST':
        action = req.POST.get('action')
        if action == 'toggle_active':
            user_id = req.POST.get('user_id')
            user = get_object_or_404(CustomUser, id=user_id)
            user.is_active = not user.is_active
            user.save()
            status_str = "activated" if user.is_active else "deactivated"
            messages.success(req, f"Student user {user.email} successfully {status_str}!")
            return redirect('admin_custom:trainees')
        elif action in ('approve', 'reject', 'approve_course_edit', 'reject_course_edit'):
            trainee_id = req.POST.get('trainee_id')
            trainee = get_object_or_404(TraineeProfile, id=trainee_id)
            if action == 'approve':
                trainee.approval_status = 'approved'
                trainee.save()
                messages.success(req, f"Student {trainee.user.email} has been approved for placements.")
                Notification.objects.create(
                    user=trainee.user,
                    title="Profile Approved for Placements",
                    message="Congratulations! Your profile has been approved by the Placement Admin. You can now apply for job openings.",
                    notification_type=Notification.Type.STATUS_UPDATE
                ).dispatch_email()
            elif action == 'reject':
                trainee.approval_status = 'rejected'
                trainee.save()
                messages.warning(req, f"Student {trainee.user.email} profile verification has been rejected.")
                Notification.objects.create(
                    user=trainee.user,
                    title="Profile Verification Status Update",
                    message="Your profile verification was rejected by the Placement Admin. Please reach out to the placement cell.",
                    notification_type=Notification.Type.STATUS_UPDATE
                ).dispatch_email()
            elif action == 'approve_course_edit':
                trainee.approval_status = 'approved'
                trainee.course_edit_request_status = 'approved'
                trainee.save()
                messages.success(req, f"Course edit request for trainee {trainee.user.email} has been approved.")
                Notification.objects.create(
                    user=trainee.user,
                    title="Course Edit Request Approved",
                    message="Your request to edit course details has been approved. You have regained full access to your placement dashboard.",
                    notification_type=Notification.Type.STATUS_UPDATE
                ).dispatch_email()
            elif action == 'reject_course_edit':
                trainee.is_course_editable = False
                trainee.course_edit_request_status = 'rejected'
                trainee.save()
                messages.warning(req, f"Course edit request for trainee {trainee.user.email} has been rejected.")
                Notification.objects.create(
                    user=trainee.user,
                    title="Course Edit Request Rejected",
                    message="Your request to edit course details was rejected.",
                    notification_type=Notification.Type.STATUS_UPDATE
                ).dispatch_email()
            return redirect('admin_custom:trainees')

    return render(req, 'admin/trainees.html', {
        'trainees': trainees,
        'q': q,
        'detail_student': detail_student
    })

@login_required
@user_passes_test(is_admin, login_url='accounts:login_admin')
def admin_recruiters_view(req):
    """
    Administrate corporate recruiter profiles, approve or reject organization registrations,
    and inspect company website details.
    """
    recruiters = RecruiterProfile.objects.all().select_related('user')

    if req.method == 'POST':
        recruiter_id = req.POST.get('recruiter_id')
        action = req.POST.get('action')
        recruiter = get_object_or_404(RecruiterProfile, id=recruiter_id)

        if action == 'approve':
            recruiter.is_approved_by_admin = True
            recruiter.save()
            messages.success(req, f"Recruiter '{recruiter.company_name}' approved successfully!")
        elif action == 'reject':
            recruiter.is_approved_by_admin = False
            recruiter.save()
            messages.warning(req, f"Recruiter '{recruiter.company_name}' verification disapproved.")
        elif action == 'toggle_active':
            user = recruiter.user
            user.is_active = not user.is_active
            user.save()
            status_str = "activated" if user.is_active else "deactivated"
            messages.success(req, f"Recruiter user {user.email} successfully {status_str}!")
        return redirect('admin_custom:recruiters')

    return render(req, 'admin/recruiters.html', {
        'recruiters': recruiters
    })

@login_required
@user_passes_test(is_admin, login_url='accounts:login_admin')
def admin_officers_view(req):
    """
    Administrate placement trainer profiles, approve or reject their registrations,
    and activate/deactivate accounts.
    """
    trainers = TrainerProfile.objects.all().select_related('user').prefetch_related('courses_handled')

    if req.method == 'POST':
        officer_id = req.POST.get('officer_id')
        action = req.POST.get('action')
        trainer = get_object_or_404(TrainerProfile, id=officer_id)

        if action == 'approve':
            trainer.is_approved = True
            trainer.save()
            messages.success(req, f"Trainer '{trainer.user.email}' approved successfully!")
        elif action == 'reject':
            trainer.is_approved = False
            trainer.save()
            messages.warning(req, f"Trainer '{trainer.user.email}' verification disapproved.")
        elif action == 'toggle_active':
            user = trainer.user
            user.is_active = not user.is_active
            user.save()
            status_str = "activated" if user.is_active else "deactivated"
            messages.success(req, f"Trainer user {user.email} successfully {status_str}!")
        return redirect('admin_custom:trainers')

    return render(req, 'admin/trainers.html', {
        'trainers': trainers
    })

@login_required
@user_passes_test(is_admin, login_url='accounts:login_admin')
def admin_jobs_view(req):
    """
    Manage published job vacancies across the platform.
    Allows editing criteria details, filtering by status (open/closed), and deletion.
    """
    status_filter = req.GET.get('status', '')
    if status_filter == 'open':
        jobs = Job.objects.filter(is_active=True).select_related('recruiter')
    elif status_filter == 'closed':
        jobs = Job.objects.filter(is_active=False).select_related('recruiter')
    else:
        jobs = Job.objects.all().select_related('recruiter')

    edit_job = None
    edit_form = None
    edit_id = req.GET.get('edit_id')
    if edit_id:
        edit_job = get_object_or_404(Job, id=edit_id)
        edit_form = JobForm(instance=edit_job)

    if req.method == 'POST':
        action = req.POST.get('action')
        if action == 'delete':
            job_id = req.POST.get('job_id')
            job = get_object_or_404(Job, id=job_id)
            job.delete()
            messages.warning(req, f"Job vacancy '{job.title}' deleted successfully!")
            return redirect('admin_custom:jobs')
        
        elif action == 'save_edit':
            job_id = req.POST.get('job_id')
            job = get_object_or_404(Job, id=job_id)
            form = JobForm(req.POST, instance=job)
            if form.is_valid():
                form.save()
                messages.success(req, f"Job '{job.title}' specs updated successfully!")
                return redirect('admin_custom:jobs')
            else:
                messages.error(req, "Validation error: Check job specs parameters.")
                edit_job = job
                edit_form = form

    return render(req, 'admin/jobs.html', {
        'jobs': jobs,
        'status_filter': status_filter,
        'edit_job': edit_job,
        'edit_form': edit_form
    })

@login_required
@user_passes_test(is_admin, login_url='accounts:login_admin')
def admin_applications_view(req):
    """
    Monitor and audit candidate applications status logs.
    Supports filtering based on pipeline shifts.
    """
    status_filter = req.GET.get('status', '')
    if status_filter:
        applications = Application.objects.filter(status=status_filter).select_related('trainee', 'trainee__user', 'job')
    else:
        applications = Application.objects.all().select_related('trainee', 'trainee__user', 'job')

    status_choices = Status.choices

    return render(req, 'admin/applications.html', {
        'applications': applications,
        'status_filter': status_filter,
        'status_choices': status_choices
    })


@login_required
@user_passes_test(is_admin, login_url='accounts:login_admin')
def admin_analytics_view(req):
    """
    Phase 5 - Administrative Control Room Placement Analytics.
    Aggregates institute placement statistics, cohort metrics, and active partner distributions.
    """
    from django.db.models import Avg, Count
    
    # 1. Core Platform Statistics
    total_students = TraineeProfile.objects.count()
    placed_students = Application.objects.filter(status='OFFER_ACCEPTED').values('trainee').distinct().count()
    placement_rate = round((placed_students / total_students * 100), 1) if total_students > 0 else 0.0
    
    avg_cgpa = TraineeProfile.objects.aggregate(avg_val=Avg('cgpa'))['avg_val']
    avg_cgpa = round(float(avg_cgpa), 2) if avg_cgpa else 0.0
    
    # 2. Placements by Branch (Horizontal bar comparisons)
    raw_branch_placements = Application.objects.filter(status='OFFER_ACCEPTED')\
        .values('trainee__branch')\
        .annotate(count=Count('id'))\
        .order_by('-count')[:5]
    
    branch_placements = []
    max_branch_count = max([b['count'] for b in raw_branch_placements]) if raw_branch_placements else 1
    for b in raw_branch_placements:
        branch_placements.append({
            'branch': b['trainee__branch'] or 'Unknown Branch',
            'count': b['count']
        })
        
    # 3. Placements by Batch (Conic-gradient Pie chart layout)
    raw_batch_placements = Application.objects.filter(status='OFFER_ACCEPTED')\
        .values('trainee__batch_code')\
        .annotate(count=Count('id'))\
        .order_by('-count')[:6]
        
    batch_placements = []
    total_batch_placements = sum([b['count'] for b in raw_batch_placements])
    batch_colors = ['#3b82f6', '#06b6d4', '#f59e0b', '#10b981', '#8b5cf6', '#ef4444']
    batch_segments = []
    current_deg = 0
    
    for idx, b in enumerate(raw_batch_placements):
        color = batch_colors[idx % len(batch_colors)]
        batch_placements.append({
            'batch_code': b['trainee__batch_code'] or 'Unknown Batch',
            'count': b['count'],
            'color': color
        })
        if total_batch_placements > 0:
            deg = (b['count'] / total_batch_placements) * 360
            batch_segments.append(f"{color} {current_deg}deg {current_deg + deg}deg")
            current_deg += deg
            
    if total_batch_placements == 0:
        batch_conic_style = "background: #475569;"
    else:
        batch_conic_style = f"background: conic-gradient({', '.join(batch_segments)});"
        
    # 4. Top Hiring Companies (Vertical column chart)
    raw_company_placements = Application.objects.filter(status='OFFER_ACCEPTED')\
        .values('job__recruiter__company_name')\
        .annotate(count=Count('id'))\
        .order_by('-count')[:5]
        
    company_placements = []
    max_company_count = max([c['count'] for c in raw_company_placements]) if raw_company_placements else 1
    for c in raw_company_placements:
        company_placements.append({
            'company': c['job__recruiter__company_name'] or 'Unknown Partner',
            'count': c['count']
        })

    # 5. Current Active Metrics
    total_partners = RecruiterProfile.objects.count()
    open_vacancies = Job.objects.filter(is_active=True).count()
    total_applications = Application.objects.count()
    successful_placements = Application.objects.filter(status='OFFER_ACCEPTED').count()

    context = {
        'total_students': total_students,
        'placement_rate': placement_rate,
        'avg_cgpa': avg_cgpa,
        
        # Placements by branch
        'branch_placements': branch_placements,
        'max_branch_count': max_branch_count,
        
        # Placements by batch
        'batch_placements': batch_placements,
        'batch_conic_style': batch_conic_style,
        'total_batch_placements': total_batch_placements,
        
        # Top hiring companies
        'company_placements': company_placements,
        'max_company_count': max_company_count,
        
        # Operational indicators
        'total_partners': total_partners,
        'open_vacancies': open_vacancies,
        'total_applications': total_applications,
        'successful_placements': successful_placements,
    }
    return render(req, 'admin/analytics.html', context)
