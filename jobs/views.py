# jobs/views.py
"""
Job posting and filtering controller views.
Enforces eligible qualification metrics and processes company recruitment submissions.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from .models import Job
from recruiters.models import RecruiterProfile
from accounts.models import TraineeProfile
from accounts.models import Role, Course, TrainerProfile
from notifications.models import Notification

def can_post_jobs(user):
    return user.is_authenticated and (user.profile.role == Role.RECRUITER or user.is_superuser)

@login_required
def active_jobs_feed_view(req):
    """
    Renders filtered active jobs feed for trainee exploration.
    Grey-outs roles where the candidate fails eligible CGPA criteria or course logic.
    """
    jobs = Job.objects.filter(is_active=True, application_deadline__gte=timezone.now().date()).select_related('recruiter').prefetch_related('required_courses')
    
    # Process search filters
    search_q = req.GET.get('q', '')
    if search_q:
        jobs = jobs.filter(title__icontains=search_q) | jobs.filter(description__icontains=search_q)
        
    loc_filter = req.GET.get('location', '')
    if loc_filter:
        jobs = jobs.filter(location__iexact=loc_filter)

    # Fetch trainee profile to contrast eligibility metrics
    trainee = None
    applied_job_ids = []
    course_eligible_job_ids = []
    experience_eligible_job_ids = []
    if req.user.profile.role == Role.TRAINEE:
        try:
            trainee = req.user.trainee_profile
            applied_job_ids = list(trainee.applications.values_list('job_id', flat=True))
            
            # Check course eligibility for each job
            student_courses = list(trainee.courses.values_list('id', flat=True))
            for job in jobs:
                job_required_course_ids = list(job.required_courses.values_list('id', flat=True))
                # If job has no required courses, anyone is course-eligible
                # Otherwise, trainee must have at least one course that matches the job's required courses
                if not job_required_course_ids or any(c_id in student_courses for c_id in job_required_course_ids):
                    course_eligible_job_ids.append(job.id)
                
                # Check experience eligibility for each job
                if trainee.experience_years >= job.experience_required:
                    experience_eligible_job_ids.append(job.id)
        except TraineeProfile.DoesNotExist:
            pass

    # Mark unread job alerts as read
    if req.user.role == Role.TRAINEE:
        req.user.notifications.filter(notification_type='JOB_ALERT', is_read=False).update(is_read=True)

    return render(req, 'jobs/feed.html', {
        'jobs': jobs, 
        'trainee': trainee,
        'search_q': search_q,
        'loc_filter': loc_filter,
        'applied_job_ids': applied_job_ids,
        'course_eligible_job_ids': course_eligible_job_ids,
        'experience_eligible_job_ids': experience_eligible_job_ids
    })

@login_required
@user_passes_test(can_post_jobs, login_url='accounts:login')
def post_new_job_view(req):
    """
    Receives custom recruiter inputs and publishes active vacancy listings.
    """
    recruiter = get_object_or_404(RecruiterProfile, user=req.user)
    
    if req.method == 'POST':
        title = req.POST.get('title')
        description = req.POST.get('description')
        job_type = req.POST.get('job_type', Job.JobType.FULL_TIME)
        location = req.POST.get('location', 'Bengaluru, IND')
        salary_package = req.POST.get('salary_package') or req.POST.get('salary')
        min_cgpa = req.POST.get('min_cgpa') or req.POST.get('min_cgpa_required') or 6.00
        deadline = req.POST.get('deadline') or req.POST.get('application_deadline')
        
        # Parse technical tags comma line or JSON list
        raw_skills = req.POST.get('skills') or req.POST.get('skills_required') or ""
        import json
        try:
            skills = json.loads(raw_skills)
            if not isinstance(skills, list):
                skills = [skills]
        except (json.JSONDecodeError, TypeError):
            skills = [s.strip() for s in raw_skills.split(',') if s.strip()]

        job = Job.objects.create(
            recruiter=recruiter,
            title=title,
            description=description,
            job_type=job_type,
            location=location,
            salary_package=salary_package,
            min_cgpa_required=min_cgpa,
            skills_required=skills,
            application_deadline=deadline
        )
        
        # Save required courses ManyToMany relationship
        required_course_ids = req.POST.getlist('required_courses')
        if required_course_ids:
            job.required_courses.set(required_course_ids)
            
        # Dispatch notifications based on course eligibility
        job_course_ids = list(job.required_courses.values_list('id', flat=True))
        
        # 1. Notify approved trainees matching courses
        matching_students = TraineeProfile.objects.filter(approval_status='approved')
        if job_course_ids:
            matching_students = matching_students.filter(courses__id__in=job_course_ids).distinct()
        
        for trainee_profile in matching_students:
            Notification.objects.create(
                user=trainee_profile.user,
                title="New Eligible Job Opportunity",
                message=f"A new job '{job.title}' has been posted by {recruiter.company_name} that matches your course profile. Apply before {job.application_deadline}.",
                notification_type=Notification.Type.JOB_ALERT
            ).dispatch_email()

        # 2. Notify approved placement trainers handling these courses
        matching_officers = TrainerProfile.objects.filter(is_approved=True)
        if job_course_ids:
            matching_officers = matching_officers.filter(courses_handled__id__in=job_course_ids).distinct()
        
        for officer_profile in matching_officers:
            Notification.objects.create(
                user=officer_profile.user,
                title="New Job in Your Handled Domains",
                message=f"A new job '{job.title}' by {recruiter.company_name} matches the courses you handle. You can now recommend trainees for this position.",
                notification_type=Notification.Type.JOB_ALERT
            ).dispatch_email()
        
        messages.success(req, f"Job Role '{job.title}' posted successfully!")
        return redirect('recruiters:dashboard')
        
    return render(req, 'jobs/publish.html', {
        'courses': Course.objects.all()
    })
