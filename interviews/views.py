# interviews/views.py
"""
Interview Scheduling and Evaluation Views.
Coordinates slot scheduling, digital meeting coordinate dispatches,
evaluation scores, and role-based portals with active status notifications.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import Interview
from .forms import InterviewForm, InterviewEvaluationForm
from applications.models import Application, Status, Offer
from accounts.models import Role
from accounts.models import TraineeProfile
from recruiters.models import RecruiterProfile
from notifications.models import Notification

def is_recruiter(user):
    return user.is_authenticated and user.profile.role == Role.RECRUITER

def is_student(user):
    return user.is_authenticated and user.profile.role == Role.TRAINEE


@login_required
@user_passes_test(is_student, login_url='accounts:login')
def student_interview_dashboard_view(req):
    """
    Phase 6 - Student Interviews Dashboard.
    Sorts upcoming meetings and tracks completed evaluations and grades.
    """
    trainee = get_object_or_404(TraineeProfile, user=req.user)
    
    # Track all scheduled / future interviews for this candidate
    interviews = Interview.objects.filter(application__trainee=trainee).select_related('application__job', 'application__job__recruiter')
    
    # Find applications that have associated interviews (meaning they got shortlisted to them)
    shortlisted_apps = Application.objects.filter(
        trainee=trainee, 
        interviews__isnull=False
    ).distinct().select_related('job', 'job__recruiter')
    
    selected_app_id = req.GET.get('application_id')
    selected_app = None
    if selected_app_id:
        try:
            selected_app = shortlisted_apps.filter(id=int(selected_app_id)).first()
        except ValueError:
            pass
            
    if not selected_app and shortlisted_apps.exists():
        selected_app = shortlisted_apps.first()
        
    upcoming = interviews.filter(status=Interview.Status.SCHEDULED).order_by('scheduled_at')
    
    if selected_app:
        historic = interviews.exclude(status=Interview.Status.SCHEDULED).filter(application=selected_app)
    else:
        historic = Interview.objects.none()

    return render(req, 'interviews/student_dashboard.html', {
        'trainee': trainee,
        'upcoming_interviews': upcoming,
        'historic_interviews': historic,
        'shortlisted_applications': shortlisted_apps,
        'selected_application': selected_app
    })


@login_required
@user_passes_test(is_recruiter, login_url='accounts:login')
def recruiter_interview_dashboard_view(req):
    """
    Phase 6 - Recruiter Interview Management Terminal.
    Lists slots to conduct, completed histories, and applicants ready for scheduling.
    """
    recruiter = get_object_or_404(RecruiterProfile, user=req.user)
    
    # Filter interviews for jobs owned by this recruiter
    interviews = Interview.objects.filter(application__job__recruiter=recruiter).select_related('application__trainee', 'application__job')
    
    scheduled = interviews.filter(status=Interview.Status.SCHEDULED).order_by('scheduled_at')
    completed = interviews.filter(status=Interview.Status.COMPLETED)
    cancelled = interviews.filter(status=Interview.Status.CANCELLED)

    # Compile candidates waiting for an interview (Shortlisted or Interviewing profiles with no active/scheduled interviews)
    shortlisted_apps = Application.objects.filter(
        job__recruiter=recruiter, 
        status__in=[Status.SHORTLISTED, Status.INTERVIEWING]
    ).exclude(
        interviews__status=Interview.Status.SCHEDULED
    ).distinct().select_related('trainee', 'job')

    # Candidates ready for placement offers (Completed high score interviews, status is INTERVIEWING or SHORTLISTED)
    eval_apps = Application.objects.filter(
        job__recruiter=recruiter, 
        status=Status.INTERVIEWING
    ).select_related('trainee', 'job')

    return render(req, 'interviews/recruiter_dashboard.html', {
        'recruiter': recruiter,
        'scheduled_interviews': scheduled,
        'completed_interviews': completed,
        'cancelled_interviews': cancelled,
        'shortlisted_applications': shortlisted_apps,
        'evaluated_applications': eval_apps
    })


@login_required
@user_passes_test(is_recruiter, login_url='accounts:login')
def schedule_interview_view(req, app_id):
    """
    Phase 5 - Interview Scheduling.
    Sets up a calendar meeting coordinate line for a shortlisted candidate.
    """
    application = get_object_or_404(Application, id=app_id)
    recruiter = get_object_or_404(RecruiterProfile, user=req.user)
    
    # Recruiter verification check
    if application.job.recruiter != recruiter:
        messages.error(req, "Access denied: unauthorized operation.")
        return redirect('interviews:recruiter_dashboard')

    if req.method == 'POST':
        form = InterviewForm(req.POST)
        if form.is_valid():
            interview = form.save(commit=False)
            interview.application = application
            interview.status = Interview.Status.SCHEDULED
            interview.save()

            # Automatically transition candidate application status to INTERVIEWING
            application.status = Status.INTERVIEWING
            application.save()

            # Phase 8 Notification and Email triggers
            notif = Notification.objects.create(
                user=application.trainee.user,
                title="Placement Interview Scheduled",
                message=f"You are formally invited to interview for position '{application.job.title}' with {recruiter.company_name}.\n"
                        f"Round: {interview.title} | Stage: {interview.get_stage_display()}\n"
                        f"Datetime: {interview.scheduled_at.strftime('%Y-%m-%d %H:%M')}\n"
                        f"Platform: {interview.platform} | Link: {interview.meet_url or 'Provided by recruiter'}",
                notification_type=Notification.Type.INTERVIEW_INVITATION
            )
            notif.dispatch_email()

            messages.success(req, f"Interview slot successfully scheduled for {application.trainee.user.get_full_name()}!")
            return redirect('interviews:recruiter_dashboard')
    else:
        # Count existing interviews to suggest round title
        existing_count = application.interviews.count()
        suggested_title = f"Technical Round {existing_count + 1}" if existing_count < 2 else "HR Round"
        form = InterviewForm(initial={'title': suggested_title, 'platform': 'Google Meet'})

    return render(req, 'interview/schedule.html', {
        'form': form,
        'application': application
    })


@login_required
@user_passes_test(is_recruiter, login_url='accounts:login')
def evaluate_interview_view(req, interview_id):
    """
    Phase 4 - Evaluates conducted interview with scores, remarks and transitions.
    """
    interview = get_object_or_404(Interview, id=interview_id, application__job__recruiter__user=req.user)
    application = interview.application

    if req.method == 'POST':
        form = InterviewEvaluationForm(req.POST, instance=interview)
        if form.is_valid():
            interview = form.save()
            
            # Update application feedback
            rating_desc = f"Interview '{interview.title}' status updated to {interview.get_status_display()}. Rating Score: {interview.rating_score}/5. Remarks: {interview.feedback_notes or 'Checked.'}"
            application.feedback_notes = rating_desc
            application.save()

            # Notify Candidate
            from django.urls import reverse
            redirect_url = reverse('interviews:student_dashboard') + f"?application_id={application.id}"
            
            notif = Notification.objects.create(
                user=application.trainee.user,
                title=f"Interview Status Updated: {interview.title}",
                message=f"The hiring panel at {application.job.recruiter.company_name} has updated status for your '{interview.title}' evaluation to {interview.get_status_display()}.",
                notification_type=Notification.Type.STATUS_UPDATE,
                redirect_url=redirect_url
            )
            notif.dispatch_email()

            messages.success(req, f"Candidate evaluation successfully saved for {application.trainee.user.get_full_name()}!")
            return redirect('interviews:recruiter_dashboard')
    else:
        form = InterviewEvaluationForm(instance=interview)

    return render(req, 'interviews/evaluate.html', {
        'form': form,
        'interview': interview,
        'application': application
    })


@login_required
@user_passes_test(is_recruiter, login_url='accounts:login')
def cancel_interview_view(req, interview_id):
    """
    Phase 4 - Cancels scheduled meeting and alerts candidate.
    """
    interview = get_object_or_404(Interview, id=interview_id, application__job__recruiter__user=req.user)
    interview.status = Interview.Status.CANCELLED
    interview.save()

    # Reset application status back to Shortlisted if appropriate, or keep for records
    application = interview.application
    application.status = Status.SHORTLISTED
    application.save()

    # Notify Candidate
    notif = Notification.objects.create(
        user=application.trainee.user,
        title="Scheduled Interview Cancelled",
        message=f"Please state: Your interview schedule '{interview.title}' for '{application.job.title}' was cancelled by {application.job.recruiter.company_name}.",
        notification_type=Notification.Type.STATUS_UPDATE
    )
    notif.dispatch_email()

    messages.warning(req, "Interview slot successfully cancelled.")
    return redirect('interviews:recruiter_dashboard')
