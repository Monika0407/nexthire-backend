# recruiters/views.py
"""
Corporate partner dashboards views.
Provides job CRUD controls, applicant screening benches, workflow updates, 
and automated email dispatcher triggers.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from .models import RecruiterProfile
from .forms import CompanyProfileForm, JobForm
from accounts.models import Role, CustomUser
from jobs.models import Job
from applications.models import Application, Status
from interviews.models import Interview
from notifications.models import Notification
from datetime import datetime

# RBAC Gate helper
def is_recruiter_or_admin(user):
    """
    Blocks unauthorized candidate trainees or external users from tampering 
    with Corporate recruiting records.
    """
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.role == 'admin':
        return True
    if user.role != Role.RECRUITER:
        return False
    try:
        return user.recruiter_profile.is_approved_by_admin
    except RecruiterProfile.DoesNotExist:
        return False


@login_required
@user_passes_test(is_recruiter_or_admin, login_url='accounts:login')
def recruiter_dashboard_view(req):
    """
    Phase 2 - Recruiter Dashboard Control Room.
    Compiles live metrics: Active Jobs, Candidates Pipeline, Interviews Scheduled, and Placement Offers.
    """
    recruiter = get_object_or_404(RecruiterProfile, user=req.user)
    
    # Posted Jobs & Application indexes
    posted_jobs = recruiter.jobs.all().order_by('-posted_at')
    active_jobs_count = posted_jobs.filter(is_active=True).count()
    
    all_applications = Application.objects.filter(job__recruiter=recruiter).select_related('trainee', 'trainee__user', 'job').prefetch_related('trainee__placement_recommendations', 'trainee__placement_recommendations__recommended_by')
    total_applicants = all_applications.count()
    
    # 1. Pipeline Counter Metrics
    interviews_scheduled_count = Interview.objects.filter(
        application__job__recruiter=recruiter, 
        status=Interview.Status.SCHEDULED
    ).count()
    
    selections_count = all_applications.filter(
        status__in=[Status.OFFER_EXTENDED, Status.OFFER_ACCEPTED]
    ).count()
    
    # 2. Recent activity lists
    recent_jobs = posted_jobs[:4]
    new_applications = all_applications.filter(status=Status.PENDING)[:5]
    
    # 3. Dynamic Hiring Metrics percentages
    acceptance_rate = 0
    if total_applicants > 0:
        acceptance_rate = int((selections_count / total_applicants) * 100)
    
    context = {
        'recruiter': recruiter,
        'posted_jobs': posted_jobs,
        'applications': all_applications,
        
        # Pipeline numbers
        'active_jobs_count': active_jobs_count,
        'total_applicants': total_applicants,
        'interviews_scheduled_count': interviews_scheduled_count,
        'selections_count': selections_count,
        
        # Lists
        'recent_jobs': recent_jobs,
        'new_applications': new_applications,
        'acceptance_rate': acceptance_rate,
    }
    return render(req, 'recruiter/dashboard.html', context)


@login_required
@user_passes_test(is_recruiter_or_admin, login_url='accounts:login')
def edit_company_profile_view(req):
    """
    Phase 3 - Corporate Identity editing cockpit.
    Updates brand descriptions, URLs, and communication lines.
    """
    recruiter = get_object_or_404(RecruiterProfile, user=req.user)
    
    if req.method == 'POST':
        form = CompanyProfileForm(req.POST, instance=recruiter)
        if form.is_valid():
            form.save()
            messages.success(req, "Corporate credentials updated perfectly inside campus database registries.")
            return redirect('recruiters:dashboard')
        else:
            messages.error(req, "Validation error: Check values input formats.")
    else:
        form = CompanyProfileForm(instance=recruiter)
        
    return render(req, 'recruiter/profile.html', {
        'form': form, 
        'recruiter': recruiter
    })


@login_required
@user_passes_test(is_recruiter_or_admin, login_url='accounts:login')
def job_create_view(req):
    """
    Phase 4 - Publish job postings. Sets min CGPA eligibility conditions.
    """
    recruiter = get_object_or_404(RecruiterProfile, user=req.user)
    
    if req.method == 'POST':
        form = JobForm(req.POST)
        if form.is_valid():
            job_instance = form.save(commit=False)
            job_instance.recruiter = recruiter
            job_instance.save()
            form.save_m2m()
            
            # Dispatch notifications to all Students
            trainees = CustomUser.objects.filter(role=Role.TRAINEE)
            for trainee_user in trainees:
                notif = Notification.objects.create(
                    user=trainee_user,
                    title=f"New Job Vacancy Alert: {job_instance.title}!",
                    message=f"{recruiter.company_name} has posted a new job vacancy: '{job_instance.title}' for {job_instance.get_job_type_display()} in {job_instance.location}. Click here to apply now!",
                    notification_type=Notification.Type.JOB_ALERT
                )
                notif.dispatch_email()

            # Dispatch notifications to all Placement Officers
            trainers = CustomUser.objects.filter(role=Role.TRAINER)
            for trainer_user in trainers:
                notif = Notification.objects.create(
                    user=trainer_user,
                    title=f"New Job Vacancy Posted: {job_instance.title}",
                    message=f"{recruiter.company_name} has posted a new job vacancy: '{job_instance.title}' for {job_instance.get_job_type_display()} in {job_instance.location}. Recommend suitable candidates now!",
                    notification_type=Notification.Type.JOB_ALERT
                )
                notif.dispatch_email()
            
            messages.success(req, f"Role successfully launched! Student feeds are now viewing '{job_instance.title}'.")
            return redirect('recruiters:dashboard')
        else:
            messages.error(req, "Unacceptable parameters! Please verify inputs.")
    else:
        form = JobForm()
        
    return render(req, 'recruiter/job_form.html', {
        'form': form, 
        'recruiter': recruiter,
        'action_title': 'Publish New Job Posting'
    })


@login_required
@user_passes_test(is_recruiter_or_admin, login_url='accounts:login')
def job_edit_view(req, job_id):
    """
    Phase 4 - Modify job details. Can edit skills checklists and application deadlines.
    """
    recruiter = get_object_or_404(RecruiterProfile, user=req.user)
    job = get_object_or_404(Job, pk=job_id, recruiter=recruiter)
    
    if req.method == 'POST':
        form = JobForm(req.POST, instance=job)
        if form.is_valid():
            form.save()
            messages.success(req, f"Changes saved! Job specs for '{job.title}' are updated.")
            return redirect('recruiters:dashboard')
    else:
        form = JobForm(instance=job)
        
    return render(req, 'recruiter/job_form.html', {
        'form': form, 
        'recruiter': recruiter,
        'job': job,
        'action_title': f"Modify Specs: {job.title}"
    })


@login_required
@user_passes_test(is_recruiter_or_admin, login_url='accounts:login')
def job_delete_view(req, job_id):
    """
    Phase 4 - Quiet job deletion. Cleans up associated pipeline registers.
    """
    recruiter = get_object_or_404(RecruiterProfile, user=req.user)
    job = get_object_or_404(Job, pk=job_id, recruiter=recruiter)
    title = job.title
    job.delete()
    messages.warning(req, f"Vacant post '{title}' removed from database feeds.")
    return redirect('recruiters:dashboard')


@login_required
@user_passes_test(is_recruiter_or_admin, login_url='accounts:login')
def job_status_toggle_view(req, job_id):
    """
    Phase 4 - Instant toggle to publish or close active trainee registrations on job postings.
    """
    recruiter = get_object_or_404(RecruiterProfile, user=req.user)
    job = get_object_or_404(Job, pk=job_id, recruiter=recruiter)
    job.is_active = not job.is_active
    job.save()
    
    status_str = "Published" if job.is_active else "Closed / Inactive"
    messages.success(req, f"Status altered: '{job.title}' is now {status_str}.")
    return redirect('recruiters:dashboard')


@login_required
@user_passes_test(is_recruiter_or_admin, login_url='accounts:login')
def recruiter_jobs_list_view(req):
    """
    Lists all vacancies posted by the logged-in recruiter enterprise.
    """
    recruiter = get_object_or_404(RecruiterProfile, user=req.user)
    posted_jobs = recruiter.jobs.all().order_by('-posted_at')
    
    return render(req, 'recruiter/jobs.html', {
        'recruiter': recruiter,
        'posted_jobs': posted_jobs
    })


@login_required
@user_passes_test(is_recruiter_or_admin, login_url='accounts:login')
def view_applicants_view(req, job_id=None):
    """
    Phase 5 - Candidate screening list.
    Recruiters can inspect portfolios, look up GPA, verify skills matching, and dispatch decisions.
    """
    recruiter = get_object_or_404(RecruiterProfile, user=req.user)
    selected_job = None
    
    if job_id:
        selected_job = get_object_or_404(Job, pk=job_id, recruiter=recruiter)
        applicants_list = Application.objects.filter(job=selected_job).select_related('trainee', 'trainee__user', 'job').prefetch_related('trainee__placement_recommendations', 'trainee__placement_recommendations__recommended_by')
    else:
        applicants_list = Application.objects.filter(job__recruiter=recruiter).select_related('trainee', 'trainee__user', 'job').prefetch_related('trainee__placement_recommendations', 'trainee__placement_recommendations__recommended_by')
        
    status_filter = req.GET.get('status')
    if status_filter == 'selections':
        applicants_list = applicants_list.filter(status__in=[Status.OFFER_EXTENDED, Status.OFFER_ACCEPTED])
        
    jobs_list = recruiter.jobs.all()
    
    return render(req, 'recruiter/applicants.html', {
        'applicants': applicants_list, 
        'jobs': jobs_list, 
        'selected_job': selected_job,
        'recruiter': recruiter,
        'status_filter': status_filter,
    })


@login_required
@user_passes_test(is_recruiter_or_admin, login_url='accounts:login')
def update_application_status_view(req, app_id, next_status):
    """
    Phase 6 & 7 - State Workflow transitions with custom trainee notifications.
    Generates notification rows and sends a transactional email alert (`dispatch_email`).
    """
    recruiter = get_object_or_404(RecruiterProfile, user=req.user)
    application = get_object_or_404(Application, pk=app_id, job__recruiter=recruiter)
    trainee = application.trainee
    
    valid_statuses = [choice[0] for choice in Status.choices]
    if next_status not in valid_statuses:
        messages.error(req, "Invalid Workflow State target transition.")
        return redirect('recruiters:view_applicants')
        
    application.status = next_status
    application.save()
    
    # Phase 7 & 6 - Dynamic templates notification creation
    subject = ""
    msg = ""
    ntype = Notification.Type.STATUS_UPDATE
    
    if next_status == Status.SHORTLISTED:
        subject = f"NextHire Placement Shortlist! - {application.job.title}"
        msg = f"Fantastic news, {trainee.user.first_name or trainee.user.username}! You have been officially shortlisted by {recruiter.company_name} for the position '{application.job.title}'. Keep your inbox clear for technical test slots announcements!"
    elif next_status == Status.REJECTED:
        subject = f"Application Status Update - {application.job.title}"
        msg = f"Hello {trainee.user.first_name or trainee.user.username}, thanks for submitting your credentials for '{application.job.title}' with {recruiter.company_name}. We have thoroughly reviewed your portfolio, but regret to inform that we are moving forward with other applicants matching specific tags at this time."
    elif next_status == Status.OFFER_EXTENDED:
        subject = f"PLACEMENT OFFER EXTENDED! - {application.job.title}"
        msg = f"Hearty congratulations from the entire campus placement cell! {recruiter.company_name} has officially released a placement offer for the position '{application.job.title}'. Visit your recruitment hub to audit the salary parameters ({application.job.salary_package}) and click 'Accept'!"
        ntype = Notification.Type.ADMIN_BROADCAST
    else:
        subject = f"Application update: {application.job.title}"
        msg = f"Your application status for position '{application.job.title}' has been successfully altered to '{application.get_status_display()}' by {recruiter.company_name}."

    # Commit notification
    notif = Notification.objects.create(
        user=trainee.user,
        title=subject,
        message=msg,
        notification_type=ntype
    )
    # Trigger transactional emails dispatches
    notif.dispatch_email()
    
    messages.success(req, f"Candidate {trainee.user.get_full_name() or trainee.user.username} successfully moved to status: '{application.get_status_display()}'. Notifications dispatched!")
    return redirect('recruiters:view_applicants')


@login_required
@user_passes_test(is_recruiter_or_admin, login_url='accounts:login')
def schedule_interview_view(req, app_id):
    """
    Phase 5 & 6 - Scheduling evaluations rounds.
    Creates an Interview object, updates application status to 'INTERVIEWING', 
    and sends trainee alert cards & transactional email.
    """
    recruiter = get_object_or_404(RecruiterProfile, user=req.user)
    application = get_object_or_404(Application, pk=app_id, job__recruiter=recruiter)
    trainee = application.trainee
    
    from interviews.forms import InterviewForm
    
    if req.method == 'POST':
        form = InterviewForm(req.POST)
        if form.is_valid():
            interview = form.save(commit=False)
            interview.application = application
            interview.status = Interview.Status.SCHEDULED
            interview.save()
            
            # 2. Push Application workflow step to INTERVIEWING
            application.status = Status.INTERVIEWING
            application.save()
            
            # 3. Create trainee Alerts notification row
            msg = f"Greetings, {trainee.user.first_name or trainee.user.username}! {recruiter.company_name} has scheduled a {interview.get_stage_display()} slot for you. Details: Round: {interview.title}, Time: {interview.scheduled_at.strftime('%Y-%m-%d %I:%M %p')}, Venue/Platform: {interview.platform}. Meet Link: {interview.meet_url}."
            notif = Notification.objects.create(
                user=trainee.user,
                title=f"NextHire Interview Invitation - {application.job.title}",
                message=msg,
                notification_type=Notification.Type.INTERVIEW_INVITATION
            )
            notif.dispatch_email()
            
            messages.success(req, f"Interview slot successfully scheduled for {trainee.user.username}. Mail notifications dispatched!")
            return redirect('recruiters:view_applicants')
        else:
            messages.error(req, "Invalid Form inputs! Please check input criteria.")
    else:
        form = InterviewForm(initial={'title': 'Technical Interview - Round 1', 'platform': 'Google Meet'})
        
    return render(req, 'interview/schedule.html', {
        'form': form,
        'application': application,
        'trainee': trainee,
        'recruiter': recruiter
    })


@login_required
@user_passes_test(is_recruiter_or_admin, login_url='accounts:login')
def recruiter_analytics_view(req):
    """
    Phase 5 - Recruiter Hiring Analytics Cockpit.
    Features key counters, dynamic job-specific pie charts, and top matching candidates.
    """
    recruiter = get_object_or_404(RecruiterProfile, user=req.user)
    
    # 1. Base counters
    applications = Application.objects.filter(job__recruiter=recruiter).select_related('job', 'trainee__user')
    total_applicants = applications.count()
    placements = applications.filter(status=Status.OFFER_ACCEPTED).count()
    
    conversion_rate = round((placements / total_applicants * 100), 1) if total_applicants > 0 else 0.0
    
    # 2. Submission statuses by Job selection
    recruiter_jobs = Job.objects.filter(recruiter=recruiter)
    selected_job_id = req.GET.get('job_id')
    selected_job = None
    if selected_job_id:
        try:
            selected_job = recruiter_jobs.filter(id=int(selected_job_id)).first()
        except ValueError:
            pass
            
    if not selected_job and recruiter_jobs.exists():
        selected_job = recruiter_jobs.first()
        
    # Get status counts for selected job
    if selected_job:
        job_apps = applications.filter(job=selected_job)
        under_review = job_apps.filter(status__in=[Status.PENDING, Status.TESTING]).count()
        shortlisted = job_apps.filter(status=Status.SHORTLISTED).count()
        interviewing = job_apps.filter(status=Status.INTERVIEWING).count()
        offers = job_apps.filter(status__in=[Status.OFFER_EXTENDED, Status.OFFER_ACCEPTED]).count()
        rejected = job_apps.filter(status=Status.REJECTED).count()
    else:
        under_review = shortlisted = interviewing = offers = rejected = 0
        
    total_job_apps = under_review + shortlisted + interviewing + offers + rejected
    
    # Calculate conic gradient for the status balance pie chart
    conic_segments = []
    current_deg = 0
    colors = {
        'under_review': '#3b82f6', # blue
        'shortlisted': '#06b6d4',  # cyan
        'interviewing': '#f59e0b', # orange
        'offers': '#10b981',       # green
        'rejected': '#ef4444',     # red
    }
    
    if total_job_apps == 0:
        conic_style = "background: #475569;"
    else:
        if under_review > 0:
            deg = (under_review / total_job_apps) * 360
            conic_segments.append(f"{colors['under_review']} {current_deg}deg {current_deg + deg}deg")
            current_deg += deg
        if shortlisted > 0:
            deg = (shortlisted / total_job_apps) * 360
            conic_segments.append(f"{colors['shortlisted']} {current_deg}deg {current_deg + deg}deg")
            current_deg += deg
        if interviewing > 0:
            deg = (interviewing / total_job_apps) * 360
            conic_segments.append(f"{colors['interviewing']} {current_deg}deg {current_deg + deg}deg")
            current_deg += deg
        if offers > 0:
            deg = (offers / total_job_apps) * 360
            conic_segments.append(f"{colors['offers']} {current_deg}deg {current_deg + deg}deg")
            current_deg += deg
        if rejected > 0:
            deg = (rejected / total_job_apps) * 360
            conic_segments.append(f"{colors['rejected']} {current_deg}deg {current_deg + deg}deg")
            current_deg += deg
        conic_style = f"background: conic-gradient({', '.join(conic_segments)});"

    # 3. Top Candidates comparison chart (Horizontal bars based on AI matching score)
    top_candidates = applications.order_by('-screener_score')[:5]

    context = {
        'recruiter': recruiter,
        'total_applicants': total_applicants,
        'placements': placements,
        'conversion_rate': conversion_rate,
        
        # Job select list & selected job
        'recruiter_jobs': recruiter_jobs,
        'selected_job': selected_job,
        
        # Selected job status counts
        'under_review_count': under_review,
        'shortlisted_count': shortlisted,
        'interviewing_count': interviewing,
        'offers_count': offers,
        'rejected_count': rejected,
        'total_job_apps': total_job_apps,
        
        # Conic style
        'conic_style': conic_style,
        
        # Top candidates
        'top_candidates': top_candidates,
    }
    return render(req, 'recruiter/analytics.html', context)
