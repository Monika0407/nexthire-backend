from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q
from accounts.models import Role, TraineeProfile, RecruiterProfile, CustomUser, TrainerProfile, Course
from jobs.models import Job
from applications.models import Application
from notifications.models import Notification
from .models import CandidateRecommendation

def is_placement_officer(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.role == 'admin':
        return True
    if user.role != Role.TRAINER:
        return False
    try:
        return user.trainer_profile.is_approved
    except TrainerProfile.DoesNotExist:
        return False

@login_required
@user_passes_test(is_placement_officer, login_url='accounts:login')
def trainer_dashboard_view(request):
    total_students = TraineeProfile.objects.count()
    approved_students = TraineeProfile.objects.filter(approval_status='approved').count()
    pending_students = TraineeProfile.objects.filter(approval_status='pending').count()
    total_applications = Application.objects.count()

    try:
        trainer = request.user.trainer_profile
    except TrainerProfile.DoesNotExist:
        trainer = None

    all_courses = Course.objects.all()
    handled_course_ids = list(trainer.courses_handled.values_list('id', flat=True)) if trainer else []

    context = {
        'total_students': total_students,
        'approved_students': approved_students,
        'pending_students': pending_students,
        'total_applications': total_applications,
        'trainer': trainer,
        'courses': all_courses,
        'handled_course_ids': handled_course_ids,
    }
    return render(request, 'trainer/dashboard.html', context)

@login_required
@user_passes_test(is_placement_officer, login_url='accounts:login')
def trainer_update_courses_view(request):
    if request.method == 'POST':
        try:
            trainer = request.user.trainer_profile
            course_ids = request.POST.getlist('courses')
            new_course_ids = [int(cid) for cid in course_ids if cid.isdigit()]
            current_course_ids = list(trainer.courses_handled.values_list('id', flat=True))
            
            if request.user.is_superuser or request.user.role == 'admin':
                trainer.courses_handled.set(new_course_ids)
                messages.success(request, "Your handled courses have been updated successfully.")
                if trainer.user != request.user:
                    # Notify trainer that admin updated their courses
                    Notification.objects.create(
                        user=trainer.user,
                        title="Handled Courses Updated by Admin",
                        message="An administrator has updated your handled courses. Your verification status remains active.",
                        notification_type=Notification.Type.STATUS_UPDATE
                    ).dispatch_email()
            else:
                if sorted(current_course_ids) != sorted(new_course_ids):
                    trainer.courses_handled.set(new_course_ids)
                    trainer.is_approved = False
                    trainer.save()
                    
                    # Notify trainer
                    Notification.objects.create(
                        user=request.user,
                        title="Handled Courses Updated",
                        message="You have successfully updated your handled courses. Your account is currently pending verification approval by the admin.",
                        notification_type=Notification.Type.STATUS_UPDATE
                    ).dispatch_email()
                    
                    # Notify admins
                    admins = CustomUser.objects.filter(role=Role.ADMIN) | CustomUser.objects.filter(is_superuser=True)
                    for admin in admins.distinct():
                        Notification.objects.create(
                            user=admin,
                            title=f"Trainer Course Update: {request.user.email}",
                            message=f"Trainer {request.user.first_name or ''} {request.user.last_name or ''} ({request.user.email}) has updated their handled courses. Please review and approve their profile.",
                            notification_type=Notification.Type.STATUS_UPDATE
                        ).dispatch_email()

                    messages.warning(request, "Your handled courses have been updated. Since your domains changed, you must get approval from the admin again before performing placement trainer actions.")
                    return redirect('accounts:role_routing')
                else:
                    messages.info(request, "No changes made to handled courses.")
        except TrainerProfile.DoesNotExist:
            messages.error(request, "Placement trainer profile not found.")
    return redirect('trainer:dashboard')

@login_required
@user_passes_test(is_placement_officer, login_url='accounts:login')
def trainer_trainees_view(request):
    search_q = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    course_filter = request.GET.get('course', '')
    job_filter = request.GET.get('job_filter', '')
    handled_only = request.GET.get('handled_only', '')

    trainees = TraineeProfile.objects.all().select_related('user').prefetch_related(
        'courses',
        'applications__job__recruiter',
        'applications__interviews'
    )

    if search_q:
        trainees = trainees.filter(
            Q(user__email__icontains=search_q) |
            Q(user__first_name__icontains=search_q) |
            Q(user__last_name__icontains=search_q) |
            Q(batch_code__icontains=search_q)
        )

    if status_filter:
        trainees = trainees.filter(approval_status=status_filter)

    if course_filter:
        trainees = trainees.filter(courses__id=course_filter)

    if job_filter:
        job_obj = get_object_or_404(Job, id=job_filter)
        if job_obj.required_courses.exists():
            trainees = trainees.filter(courses__in=job_obj.required_courses.all())

    if handled_only == 'true' and request.user.role == Role.TRAINER:
        try:
            trainer = request.user.trainer_profile
            trainer_courses = trainer.courses_handled.all()
            trainees = trainees.filter(courses__in=trainer_courses)
        except TrainerProfile.DoesNotExist:
            pass

    # Ensure query results are distinct to prevent duplicates
    trainees = trainees.distinct()

    is_admin_user = request.user.is_superuser or request.user.role == 'admin'
    if is_admin_user:
        for trainee in trainees:
            trainee.can_manage = True
    else:
        try:
            trainer = request.user.trainer_profile
            trainer_course_ids = set(trainer.courses_handled.values_list('id', flat=True))
            for trainee in trainees:
                trainee_course_ids = {c.id for c in trainee.courses.all()}
                trainee.can_manage = bool(trainer_course_ids.intersection(trainee_course_ids))
        except TrainerProfile.DoesNotExist:
            for trainee in trainees:
                trainee.can_manage = False

    active_jobs = Job.objects.filter(is_active=True).select_related('recruiter').prefetch_related('required_courses')
    for trainee in trainees:
        trainee_course_ids = set(trainee.courses.values_list('id', flat=True))
        student_eligible_jobs = []
        for job in active_jobs:
            job_required_course_ids = set(job.required_courses.values_list('id', flat=True))
            if not job_required_course_ids or trainee_course_ids.intersection(job_required_course_ids):
                student_eligible_jobs.append(job)
        trainee.eligible_jobs = student_eligible_jobs
    all_courses = Course.objects.all()

    context = {
        'trainees': trainees,
        'active_jobs': active_jobs,
        'all_courses': all_courses,
        'search_q': search_q,
        'status_filter': status_filter,
        'course_filter': int(course_filter) if course_filter.isdigit() else '',
        'job_filter': int(job_filter) if job_filter.isdigit() else '',
        'handled_only': handled_only == 'true',
    }
    return render(request, 'trainer/trainees.html', context)

@login_required
@user_passes_test(is_placement_officer, login_url='accounts:login')
def trainer_approve_view(request):
    if request.method == 'POST':
        trainee_id = request.POST.get('trainee_id')
        action = request.POST.get('action')
        trainee = get_object_or_404(TraineeProfile, id=trainee_id)

        is_admin_user = request.user.is_superuser or request.user.role == 'admin'
        if not is_admin_user:
            try:
                trainer = request.user.trainer_profile
                trainer_course_ids = set(trainer.courses_handled.values_list('id', flat=True))
                trainee_course_ids = {c.id for c in trainee.courses.all()}
                if not trainer_course_ids.intersection(trainee_course_ids):
                    messages.error(request, "Permission denied: You do not handle this trainee's courses.")
                    return redirect('trainer:trainees')
            except TrainerProfile.DoesNotExist:
                messages.error(request, "Permission denied: Placement trainer profile not found.")
                return redirect('trainer:trainees')

        if action == 'approve':
            trainee.approval_status = 'approved'
            trainee.save()
            messages.success(request, f"Student {trainee.user.email} has been approved for placements.")
            
            # Notify trainee
            Notification.objects.create(
                user=trainee.user,
                title="Profile Approved for Placements",
                message="Congratulations! Your profile has been approved by the Trainer. You can now apply for job openings.",
                notification_type=Notification.Type.STATUS_UPDATE
            ).dispatch_email()
            
        elif action == 'reject':
            trainee.approval_status = 'rejected'
            trainee.save()
            messages.warning(request, f"Student {trainee.user.email} profile verification has been rejected.")
            
            # Notify trainee
            Notification.objects.create(
                user=trainee.user,
                title="Profile Verification Status Update",
                message="Your profile verification was rejected by the Trainer. Please reach out to the placement cell.",
                notification_type=Notification.Type.STATUS_UPDATE
            ).dispatch_email()

        elif action == 'approve_course_edit':
            trainee.approval_status = 'approved'
            trainee.course_edit_request_status = 'approved'
            trainee.save()
            messages.success(request, f"Course edit request for trainee {trainee.user.email} has been approved.")
            
            # Notify trainee
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
            messages.warning(request, f"Course edit request for trainee {trainee.user.email} has been rejected.")
            
            # Notify trainee
            Notification.objects.create(
                user=trainee.user,
                title="Course Edit Request Rejected",
                message="Your request to edit course details was rejected by the Trainer.",
                notification_type=Notification.Type.STATUS_UPDATE
            ).dispatch_email()

    return redirect('trainer:trainees')

@login_required
@user_passes_test(is_placement_officer, login_url='accounts:login')
def trainer_recommend_view(request):
    if request.method == 'POST':
        trainee_id = request.POST.get('trainee_id')
        job_id = request.POST.get('job_id')
        comments = request.POST.get('comments', '')

        trainee = get_object_or_404(TraineeProfile, id=trainee_id)
        job = get_object_or_404(Job, id=job_id)

        # Check trainee course eligibility for the job
        if job.required_courses.exists():
            trainee_course_ids = set(trainee.courses.values_list('id', flat=True))
            job_required_course_ids = set(job.required_courses.values_list('id', flat=True))
            if not trainee_course_ids.intersection(job_required_course_ids):
                messages.error(request, f"Permission denied: Student is not enrolled in the required courses for this job ({job.title}).")
                return redirect('trainer:trainees')

        is_admin_user = request.user.is_superuser or request.user.role == 'admin'
        if not is_admin_user:
            try:
                trainer = request.user.trainer_profile
                trainer_course_ids = set(trainer.courses_handled.values_list('id', flat=True))
                trainee_course_ids = {c.id for c in trainee.courses.all()}
                if not trainer_course_ids.intersection(trainee_course_ids):
                    messages.error(request, "Permission denied: You do not handle this trainee's courses.")
                    return redirect('trainer:trainees')

                # Check if the trainer handles any course required by the job
                if job.required_courses.exists():
                    job_course_ids = set(job.required_courses.values_list('id', flat=True))
                    if not trainer_course_ids.intersection(job_course_ids):
                        messages.error(request, f"Permission denied: You do not handle any courses eligible for this job ({job.title}).")
                        return redirect('trainer:trainees')
            except TrainerProfile.DoesNotExist:
                messages.error(request, "Permission denied: Placement trainer profile not found.")
                return redirect('trainer:trainees')

        recommendation, created = CandidateRecommendation.objects.get_or_create(
            trainee=trainee,
            job=job,
            defaults={
                'recommended_by': request.user,
                'comments': comments
            }
        )

        if created:
            messages.success(request, f"Successfully recommended trainee {trainee.user.email} for '{job.title}'.")
            
            # Notify recruiter
            Notification.objects.create(
                user=job.recruiter.user,
                title="Trainer Candidate Recommendation",
                message=f"Trainer recommended candidate {trainee.user.get_full_name() or trainee.user.email} (Batch Code: {trainee.batch_code}) for '{job.title}'. Comments: {comments}",
                notification_type=Notification.Type.STUDENT_APPLIED
            ).dispatch_email()
        else:
            messages.warning(request, f"Student {trainee.user.email} has already been recommended for '{job.title}'.")

    referer = request.META.get('HTTP_REFERER', '')
    if 'jobs' in referer:
        return redirect('trainer:jobs')
    return redirect('trainer:trainees')

@login_required
@user_passes_test(is_placement_officer, login_url='accounts:login')
def trainer_recruiters_view(request):
    search_q = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')

    recruiters = RecruiterProfile.objects.all().select_related('user')

    if search_q:
        recruiters = recruiters.filter(
            Q(company_name__icontains=search_q) |
            Q(user__email__icontains=search_q) |
            Q(contact_email__icontains=search_q)
        )

    if status_filter == 'approved':
        recruiters = recruiters.filter(is_approved_by_admin=True)
    elif status_filter == 'pending':
        recruiters = recruiters.filter(is_approved_by_admin=False)

    context = {
        'recruiters': recruiters,
        'search_q': search_q,
        'status_filter': status_filter,
    }
    return render(request, 'trainer/recruiters.html', context)

@login_required
@user_passes_test(is_placement_officer, login_url='accounts:login')
def trainer_approve_recruiter_view(request):
    if request.method == 'POST':
        recruiter_id = request.POST.get('recruiter_id')
        action = request.POST.get('action')
        recruiter = get_object_or_404(RecruiterProfile, id=recruiter_id)

        if action == 'approve':
            recruiter.is_approved_by_admin = True
            recruiter.save()
            messages.success(request, f"Recruiter {recruiter.company_name} has been approved.")
            
            # Notify recruiter
            Notification.objects.create(
                user=recruiter.user,
                title="Profile Approved",
                message=f"Congratulations! Your company profile '{recruiter.company_name}' has been approved by the Trainer.",
                notification_type=Notification.Type.STATUS_UPDATE
            ).dispatch_email()
            
        elif action == 'reject':
            recruiter.is_approved_by_admin = False
            recruiter.save()
            messages.warning(request, f"Recruiter {recruiter.company_name} profile has been rejected/disapproved.")
            
            # Notify recruiter
            Notification.objects.create(
                user=recruiter.user,
                title="Profile Disapproved",
                message="Your recruiter profile registration was rejected/disapproved. Please contact the placement cell.",
                notification_type=Notification.Type.STATUS_UPDATE
            ).dispatch_email()

    return redirect('trainer:recruiters')

@login_required
@user_passes_test(is_placement_officer, login_url='accounts:login')
def trainer_jobs_view(request):
    search_q = request.GET.get('q', '')
    jobs = Job.objects.filter(is_active=True).select_related('recruiter').prefetch_related('required_courses')
    
    if search_q:
        jobs = jobs.filter(
            Q(title__icontains=search_q) |
            Q(recruiter__company_name__icontains=search_q)
        )
        
    all_students = TraineeProfile.objects.filter(approval_status='approved').select_related('user').prefetch_related('courses')
    
    for job in jobs:
        eligible_students = []
        job_course_ids = set(job.required_courses.values_list('id', flat=True))
        for trainee in all_students:
            trainee_course_ids = set(trainee.courses.values_list('id', flat=True))
            if not job_course_ids or trainee_course_ids.intersection(job_course_ids):
                # Filter by trainer's handled courses if not admin/superuser
                is_admin_user = request.user.is_superuser or request.user.role == 'admin'
                if not is_admin_user:
                    try:
                        trainer = request.user.trainer_profile
                        trainer_course_ids = set(trainer.courses_handled.values_list('id', flat=True))
                        if trainer_course_ids.intersection(trainee_course_ids):
                            eligible_students.append(trainee)
                    except TrainerProfile.DoesNotExist:
                        pass
                else:
                    eligible_students.append(trainee)
        job.eligible_students = eligible_students

    # Mark unread job alerts as read for the trainer
    if request.user.role == Role.TRAINER:
        request.user.notifications.filter(notification_type='JOB_ALERT', is_read=False).update(is_read=True)

    context = {
        'jobs': jobs,
        'search_q': search_q,
    }
    return render(request, 'trainer/jobs.html', context)


@login_required
@user_passes_test(is_placement_officer, login_url='accounts:login')
def trainer_analytics_view(request):
    """
    Phase 5 - Trainer Placement Analytics Console.
    Analyzes student enrollments, batch distributions, and operational indicators with visual indicators.
    """
    from django.db.models import Count
    
    total_students = TraineeProfile.objects.count()
    approved_students = TraineeProfile.objects.filter(approval_status='approved').count()
    pending_students = TraineeProfile.objects.filter(approval_status='pending').count()
    open_jobs = Job.objects.filter(is_active=True).count()
    placed_students = Application.objects.filter(status='OFFER_ACCEPTED').values('trainee').distinct().count()
    recruiters_active = RecruiterProfile.objects.filter(is_approved_by_admin=True).count()
    
    # Top Course Enrollments
    course_data = Course.objects.annotate(trainee_count=Count('students')).order_by('-trainee_count')[:6]
    max_course_count = max([c.trainee_count for c in course_data]) if course_data else 1
    
    # Batch Distribution
    raw_batch_data = TraineeProfile.objects.values('batch_code').annotate(count=Count('id')).order_by('-count')[:6]
    batch_data = []
    total_batch_students = sum([b['count'] for b in raw_batch_data])
    
    batch_colors = ['#3b82f6', '#06b6d4', '#f59e0b', '#10b981', '#8b5cf6', '#ef4444']
    batch_segments = []
    current_deg = 0
    
    for idx, b in enumerate(raw_batch_data):
        color = batch_colors[idx % len(batch_colors)]
        batch_item = {
            'batch_code': b['batch_code'],
            'count': b['count'],
            'color': color
        }
        batch_data.append(batch_item)
        if total_batch_students > 0:
            deg = (b['count'] / total_batch_students) * 360
            batch_segments.append(f"{color} {current_deg}deg {current_deg + deg}deg")
            current_deg += deg
            
    if total_batch_students == 0:
        batch_conic_style = "background: #475569;"
    else:
        batch_conic_style = f"background: conic-gradient({', '.join(batch_segments)});"
    
    # Operational Signals
    pending_course_requests = TraineeProfile.objects.filter(course_edit_request_status='pending').count()
    placement_recommendations = CandidateRecommendation.objects.count()
    
    context = {
        'total_students': total_students,
        'approved_students': approved_students,
        'pending_students': pending_students,
        'open_jobs': open_jobs,
        'placed_students': placed_students,
        'recruiters_active': recruiters_active,
        
        # Lists for charts
        'course_data': course_data,
        'max_course_count': max_course_count,
        'batch_data': batch_data,
        'batch_conic_style': batch_conic_style,
        
        # Operational signals
        'pending_course_requests': pending_course_requests,
        'placement_recommendations': placement_recommendations,
    }
    return render(request, 'trainer/analytics.html', context)
