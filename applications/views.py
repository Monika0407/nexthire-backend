# applications/views.py
"""
Job application controllers.
Implements eligibility criteria audits, state transitions, application tracking,
withdraw actions, and Phase 7 select offer lifecycles with real-time Phase 8 and SMTP alerts.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpResponse, HttpResponseForbidden
from .models import Application, Status, Offer, OfferStatus
from .forms import OfferForm
from jobs.models import Job
from accounts.models import TraineeProfile
from recruiters.models import RecruiterProfile
from accounts.models import Role
from notifications.models import Notification

def is_student(user):
    return user.is_authenticated and user.profile.role == Role.TRAINEE

def is_recruiter(user):
    return user.is_authenticated and user.profile.role == Role.RECRUITER

@login_required
@user_passes_test(is_student, login_url='accounts:login')
def apply_job_view(req, job_id):
    """
    Two-Phase AI Resume Analyser and Final Submission workflow using BERT/SBERT.
    """
    job = get_object_or_404(Job, id=job_id, is_active=True)
    trainee = get_object_or_404(TraineeProfile, user=req.user)

    # Check application deadline compliance
    from django.utils import timezone
    if job.application_deadline < timezone.now().date():
        messages.error(
            req,
            "Submission blocked: The application deadline for this position has passed."
        )
        return redirect('jobs:feed')

    # 0. Check placement trainer approval status
    if trainee.approval_status != 'approved':
        messages.error(
            req,
            "Submission blocked: Your profile is pending verification or has been rejected by the Trainer."
        )
        return redirect('jobs:feed')

    # 1. Check CGPA compliance
    if trainee.cgpa < job.min_cgpa_required:
        messages.error(
            req, 
            f"Submission blocked: This position requires minimum CGPA of {job.min_cgpa_required}. Your current CGPA is {trainee.cgpa}."
        )
        return redirect('jobs:feed')

    # Course eligibility check
    if job.required_courses.exists():
        student_courses = trainee.courses.all()
        if not job.required_courses.filter(id__in=student_courses).exists():
            messages.error(
                req,
                f"Submission blocked: This position is not open to your course. Eligible courses: {', '.join([c.name for c in job.required_courses.all()])}."
            )
            return redirect('jobs:feed')

    # Experience eligibility check
    if trainee.experience_years < job.experience_required:
        messages.error(
            req,
            f"Submission blocked: This position requires minimum {job.experience_required} year(s) of experience. Your profile lists {trainee.experience_years} year(s)."
        )
        return redirect('jobs:feed')

    # 2. Prevent duplicate entries
    if Application.objects.filter(trainee=trainee, job=job).exists():
        messages.warning(req, "You have already applied for this opening.")
        return redirect('trainees:dashboard')

    # Get session analysis details
    analysis_results = req.session.get(f'analysis_{job_id}')
    temp_resume_name = req.session.get(f'temp_resume_name_{job_id}')

    if req.method == 'POST':
        action = req.POST.get('action')

        if not action:
            # Direct application compatibility fallback (e.g. tests or direct POST)
            from trainees.models import Resume
            active_resume = Resume.objects.filter(trainee=trainee, is_active=True).first()
            if not active_resume and trainee.resume_file:
                active_resume = Resume.objects.create(trainee=trainee, resume_file=trainee.resume_file, is_active=True)
            
            app = Application.objects.create(
                trainee=trainee,
                job=job,
                resume=active_resume,
                status=Status.PENDING,
                screener_score=75
            )

            # Send notifications
            s_notify = Notification.objects.create(
                user=req.user,
                title="Application Submitted Successfully",
                message=f"Your application for '{job.title}' with {job.recruiter.company_name} has been filed under 'Under Review'.",
                notification_type=Notification.Type.STATUS_UPDATE
            )
            s_notify.dispatch_email()

            r_notify = Notification.objects.create(
                user=job.recruiter.user,
                title="New Campaign Submittal",
                message=f"Candidate {trainee.user.get_full_name() or trainee.user.username} has applied for '{job.title}'.",
                notification_type=Notification.Type.STUDENT_APPLIED
            )
            r_notify.dispatch_email()

            messages.success(req, f"Successfully submitted application for '{job.title}'!")
            return redirect('applications:tracking')

        if action == 'clear_analysis':
            # Re-analyze option: reset state
            req.session.pop(f'analysis_{job_id}', None)
            req.session.pop(f'temp_resume_name_{job_id}', None)
            return redirect('applications:apply', job_id=job_id)

        elif action == 'analyze':
            # Phase 1 - Resume upload and SBERT Analysis
            resume_file = req.FILES.get('resume_file')
            if not resume_file:
                messages.error(req, "Please select a resume file to upload.")
                return redirect('applications:apply', job_id=job_id)

            filename = resume_file.name.lower()
            if not (filename.endswith('.pdf') or filename.endswith('.docx')):
                messages.error(req, "Invalid file format: Please upload a PDF (.pdf) or Word (.docx) document.")
                return redirect('applications:apply', job_id=job_id)

            try:
                extracted_text = ""
                if filename.endswith('.pdf'):
                    import fitz  # PyMuPDF
                    doc = fitz.open(stream=resume_file.read(), filetype="pdf")
                    for page in doc:
                        extracted_text += page.get_text()
                else:
                    import docx
                    doc = docx.Document(resume_file)
                    extracted_text = "\n".join([para.text for para in doc.paragraphs])

                if not extracted_text.strip():
                    messages.error(req, "Could not extract readable text from the uploaded document. Make sure it contains text rather than scanned images.")
                    return redirect('applications:apply', job_id=job_id)

                # Run SBERT analyzer
                from resume_analyzer import analyze_resume_sbert
                results = analyze_resume_sbert(
                    extracted_text,
                    job.title,
                    job.description,
                    job.skills_required or []
                )

                req.session[f'analysis_{job_id}'] = results
                req.session[f'temp_resume_name_{job_id}'] = resume_file.name
                messages.success(req, "Resume Analysis completed successfully!")
                return redirect('applications:apply', job_id=job_id)

            except Exception as e:
                messages.error(req, f"Resume parsing failure: {e}")
                return redirect('applications:apply', job_id=job_id)

        elif action == 'finalize':
            # Phase 2 - Final submission of improved resume
            final_resume_file = req.FILES.get('final_resume_file')
            if not final_resume_file:
                messages.error(req, "Please upload your improved final resume.")
                return redirect('applications:apply', job_id=job_id)

            filename = final_resume_file.name.lower()
            if not (filename.endswith('.pdf') or filename.endswith('.docx')):
                messages.error(req, "Invalid file format: Please upload a PDF (.pdf) or Word (.docx) document.")
                return redirect('applications:apply', job_id=job_id)

            try:
                from trainees.models import Resume
                # Deactivate trainee's previous active resumes
                Resume.objects.filter(trainee=trainee, is_active=True).update(is_active=False)

                # Update TraineeProfile model fields
                trainee.resume_file = final_resume_file
                trainee.save()

                # Create new active Resume
                new_resume = Resume.objects.create(
                    trainee=trainee,
                    resume_file=final_resume_file,
                    is_active=True
                )

                # Calculate score
                screener_score = 75
                if analysis_results:
                    screener_score = int(analysis_results.get('similarity_score', 75))

                # Create final Application
                app = Application.objects.create(
                    trainee=trainee,
                    job=job,
                    resume=new_resume,
                    status=Status.PENDING,
                    screener_score=screener_score
                )

                # Send notifications
                s_notify = Notification.objects.create(
                    user=req.user,
                    title="Application Submitted Successfully",
                    message=f"Your application for '{job.title}' with {job.recruiter.company_name} has been filed under 'Under Review' after resume evaluation.",
                    notification_type=Notification.Type.STATUS_UPDATE
                )
                s_notify.dispatch_email()

                r_notify = Notification.objects.create(
                    user=job.recruiter.user,
                    title="New Campaign Submittal",
                    message=f"Candidate {trainee.user.get_full_name() or trainee.user.username} has applied for '{job.title}'.",
                    notification_type=Notification.Type.STUDENT_APPLIED
                )
                r_notify.dispatch_email()

                # Clear session keys
                req.session.pop(f'analysis_{job_id}', None)
                req.session.pop(f'temp_resume_name_{job_id}', None)

                messages.success(req, f"Your finalized application for '{job.title}' has been successfully submitted!")
                return redirect('applications:tracking')

            except Exception as e:
                messages.error(req, f"Final submission failed: {e}")
                return redirect('applications:apply', job_id=job_id)

    # Render template with current analysis status
    return render(req, 'applications/apply_workflow.html', {
        'job': job,
        'trainee': trainee,
        'analysis_results': analysis_results,
        'temp_resume_name': temp_resume_name
    })


@login_required
@user_passes_test(is_student, login_url='accounts:login')
def withdraw_application_view(req, app_id):
    """
    Phase 2 - Allows trainee candidates to pull back submissions gracefully.
    """
    application = get_object_or_404(Application, id=app_id, student__user=req.user)
    job_title = application.job.title
    recruiter_user = application.job.recruiter.user
    
    # Check application deadline compliance
    from django.utils import timezone
    if application.job.application_deadline < timezone.now().date():
        messages.error(
            req,
            f"Withdrawal blocked: The application deadline for '{job_title}' has passed. You cannot withdraw your application after the deadline."
        )
        return redirect('applications:tracking')
        
    # Notify Recruiter of withdrawal
    rw_notify = Notification.objects.create(
        user=recruiter_user,
        title="Application Withdrawn",
        message=f"Candidate {req.user.get_full_name() or req.user.username} withdrew their application for '{job_title}'.",
        notification_type=Notification.Type.STUDENT_APPLIED
    )
    rw_notify.dispatch_email()
    
    application.delete()
    messages.info(req, f"Successfully withdrew application for '{job_title}'.")
    return redirect('applications:tracking')


@login_required
@user_passes_test(is_student, login_url='accounts:login')
def student_applications_tracking_view(req):
    """
    Phase 3 - Comprehensive Application Tracking Panel with Search and Filter.
    Displays Active Applications, timeline trackers, and detailed recruiter remarks.
    """
    trainee = get_object_or_404(TraineeProfile, user=req.user)
    all_apps = Application.objects.filter(trainee=trainee).select_related('job', 'job__recruiter')

    # Auto-healing for offers bypassed by recruiter direct status changes
    for app in all_apps:
        if app.status in [Status.OFFER_EXTENDED, Status.OFFER_ACCEPTED]:
            from .models import Offer, OfferStatus
            if not Offer.objects.filter(trainee=trainee, job=app.job).exists():
                Offer.objects.create(
                    trainee=trainee,
                    company=app.job.recruiter,
                    job=app.job,
                    package=app.job.salary_package or "Not Specified",
                    status=OfferStatus.ACCEPTED if app.status == Status.OFFER_ACCEPTED else OfferStatus.PENDING,
                    offer_letter_text=f"Dear {trainee.user.get_full_name() or trainee.user.username},\n\nWe are delighted to extend this formal offer of recruitment for the position of '{app.job.title}' with {app.job.recruiter.company_name}.\n\nCompensation details: {app.job.salary_package or 'Competitive salary package'}\nReporting headquarters: {app.job.location}\n\nWelcome aboard!"
                )

    if all_apps.filter(status=Status.OFFER_ACCEPTED).exists():
        if trainee.current_status != 'Placed':
            trainee.current_status = 'Placed'
            trainee.save()

    # Process search query matching job title or company name
    q = req.GET.get('q', '')
    if q:
        all_apps = all_apps.filter(job__title__icontains=q) | all_apps.filter(job__recruiter__company_name__icontains=q)

    # Process status filter logic
    status_filter = req.GET.get('status', '')
    if status_filter:
        all_apps = all_apps.filter(status=status_filter)

    # Active apps count (where status is not rejected or accepted yet)
    active_apps = all_apps.exclude(status__in=[Status.REJECTED, Status.OFFER_ACCEPTED])

    # Status choices for filter dropdown matching Status choices
    status_choices = Status.choices

    from django.utils import timezone
    return render(req, 'trainee/applications.html', {
        'trainee': trainee,
        'applications': all_apps,
        'active_apps_count': active_apps.count(),
        'q': q,
        'status_filter': status_filter,
        'status_choices': status_choices,
        'today': timezone.now().date()
    })


@login_required
@user_passes_test(is_recruiter, login_url='accounts:login')
def update_application_status_view(req, app_id):
    """
    Called by job-owning recruiters to transition candidate pipeline states. Triggers alerts.
    """
    application = get_object_or_404(Application, id=app_id)
    
    # Verify that the recruiter owns this job posting
    if application.job.recruiter.user != req.user:
        messages.error(req, "Access denied: unauthorized updates.")
        return redirect('recruiters:dashboard')

    if req.method == 'POST':
        new_status = req.POST.get('status')
        feedback = req.POST.get('feedback', '')

        if new_status in Status.values:
            application.status = new_status
            application.feedback_notes = feedback
            application.save()

            # Triggers Phase 8 Notifications
            notify = Notification.objects.create(
                user=application.trainee.user,
                title=f"Application Step Updated: {application.get_status_display()}",
                message=f"Your pipeline state for '{application.job.title}' with {application.job.recruiter.company_name} was updated to: {application.get_status_display()}. Feedback: {feedback or 'Checked. Outstanding Profile.'}",
                notification_type=Notification.Type.STATUS_UPDATE
            )
            notify.dispatch_email()

            messages.success(req, f"Application updated to: {application.get_status_display()}")
        else:
            messages.error(req, "Invalid selection parameter.")

    return redirect('recruiters:dashboard')


# =========================================================================
# Phase 7 — Offer Letters Lifecycle views
# =========================================================================

@login_required
@user_passes_test(is_recruiter, login_url='accounts:login')
def generate_offer_view(req, app_id=None):
    """
    Allows corporate recruiters to compile formal placement selection offers.
    Auto-updates application pipeline status to OFFER_EXTENDED on creation.
    """
    recruiter = get_object_or_404(RecruiterProfile, user=req.user)
    
    selected_app = None
    if app_id:
        selected_app = get_object_or_404(Application, id=app_id)
        if selected_app.job.recruiter != recruiter:
            messages.error(req, "Access denied: Unauthorized operation context.")
            return redirect('recruiters:dashboard')

    if req.method == 'POST':
        form = OfferForm(req.POST)
        form.fields['job'].queryset = Job.objects.filter(recruiter=recruiter)
        form.fields['trainee'].queryset = TraineeProfile.objects.filter(applications__job__recruiter=recruiter).distinct()
        if form.is_valid():
            offer = form.save(commit=False)
            offer.company = recruiter
            offer.status = OfferStatus.PENDING
            offer.save()

            # Update Application pipeline state
            app_to_lock = Application.objects.filter(trainee=offer.trainee, job=offer.job).first()
            if app_to_lock:
                app_to_lock.status = Status.OFFER_EXTENDED
                app_to_lock.save()

            # Dispatch Notification & Email (Phase 8)
            notif = Notification.objects.create(
                user=offer.trainee.user,
                title="Placement Draft Offer Released!",
                message=f"Congratulations! {recruiter.company_name} has released an official career placement offer letter for '{offer.job.title}' offering package {offer.package}. Review terms instantly.",
                notification_type=Notification.Type.STATUS_UPDATE
            )
            notif.dispatch_email()

            messages.success(req, f"Career Offer Letter extended successfully to {offer.trainee.user.get_full_name()}!")
            return redirect('interviews:recruiter_dashboard')
    else:
        initial_data = {}
        if selected_app:
            initial_data = {
                'trainee': selected_app.trainee,
                'job': selected_app.job,
                'package': selected_app.job.salary_package,
                'offer_letter_text': f"Dear {selected_app.trainee.user.get_full_name() or selected_app.trainee.user.username},\n\n"
                                     f"We are delighted to extend this formal offer of recruitment for the position of '{selected_app.job.title}' with {recruiter.company_name} based on our rigorous hiring evaluations.\n\n"
                                     f"Compensation details: {selected_app.job.salary_package}\n"
                                     f"Reporting headquarters: {selected_app.job.location}\n\n"
                                     f"Welcome aboard!\nCorporate Hiring Panel"
            }
        form = OfferForm(initial=initial_data)
        form.fields['job'].queryset = Job.objects.filter(recruiter=recruiter)
        form.fields['trainee'].queryset = TraineeProfile.objects.filter(applications__job__recruiter=recruiter).distinct()

    return render(req, 'applications/offer_form.html', {
        'form': form,
        'app': selected_app
    })


@login_required
@user_passes_test(is_student, login_url='accounts:login')
def accept_offer_view(req, offer_id):
    """
    Allows candidates to lock placement selections. Updates database records.
    """
    offer = get_object_or_404(Offer, id=offer_id, trainee__user=req.user, status=OfferStatus.PENDING)
    offer.status = OfferStatus.ACCEPTED
    offer.save()

    # Update trainee profile placement status
    offer.trainee.current_status = 'Placed'
    offer.trainee.save()

    # Update linked application
    linked_app = Application.objects.filter(trainee=offer.trainee, job=offer.job).first()
    if linked_app:
        linked_app.status = Status.OFFER_ACCEPTED
        linked_app.save()

    # Notify Recruiter
    notif = Notification.objects.create(
        user=offer.company.user,
        title="Placement Offer Accepted!",
        message=f"Candidate {req.user.get_full_name() or req.user.username} has accepted your placement offer for position '{offer.job.title}'. Congratulations!",
        notification_type=Notification.Type.STATUS_UPDATE
    )
    notif.dispatch_email()

    messages.success(req, f"Outstanding! You have officially accepted the placement offer from '{offer.company.company_name}'. Wishing you absolute success!")
    return redirect('applications:tracking')


@login_required
@user_passes_test(is_student, login_url='accounts:login')
def reject_offer_view(req, offer_id):
    """
    Allows candidates to decline compensation offers.
    """
    offer = get_object_or_404(Offer, id=offer_id, trainee__user=req.user, status=OfferStatus.PENDING)
    offer.status = OfferStatus.REJECTED
    offer.save()

    # Update app pipeline
    linked_app = Application.objects.filter(trainee=offer.trainee, job=offer.job).first()
    if linked_app:
        linked_app.status = Status.REJECTED
        linked_app.save()

    # Notify Recruiter
    notif = Notification.objects.create(
        user=offer.company.user,
        title="Placement Offer Rejected",
        message=f"{req.user.get_full_name() or req.user.username} has declined the offer extended for position '{offer.job.title}'.",
        notification_type=Notification.Type.STATUS_UPDATE
    )
    notif.dispatch_email()

    messages.warning(req, f"You have declined the offer extended by '{offer.company.company_name}'. Your feedback has been logged.")
    return redirect('applications:tracking')


@login_required
def download_offer_view(req, offer_id):
    """
    Generates a highly-polished, printable selection letter file download.
    Available to candidate owner and respective recruiter.
    """
    offer = get_object_or_404(Offer, id=offer_id)
    
    # Authorized access verification
    is_owner = (req.user == offer.trainee.user)
    is_recruiter = (req.user == offer.company.user) or (req.user.is_authenticated and req.user.profile.role == Role.RECRUITER and offer.company.user == req.user)
    is_admin = req.user.is_superuser or req.user.is_staff
    
    if not (is_owner or is_recruiter or is_admin):
        return HttpResponseForbidden("Access Denied: You are unauthorized to download this offer certificate.")

    # Format official plain text document layout
    divider = "=" * 80
    body = (
        f"{divider}\n"
        f"               NEXTHIRE SMART CAMPUS REGISTRY - SELECTION OFFER LETTER\n"
        f"{divider}\n\n"
        f"Date Issued: {offer.created_at.strftime('%B %Y, %d')}\n"
        f"Candidate Name: {offer.trainee.user.get_full_name() or offer.trainee.user.username}\n"
        f"Batch Code Index: {offer.trainee.batch_code}\n"
        f"Academic Branch: {offer.trainee.branch}\n\n"
        f"Dear Recipient,\n\n"
        f"{offer.offer_letter_text}\n\n"
        f"{divider}\n"
        f"Recruitment Organization details:\n"
        f"Company Name: {offer.company.company_name}\n"
        f"Compensation Package: {offer.package}\n"
        f"Job Designation: {offer.job.title}\n"
        f"Deployment Location: {offer.job.location}\n"
        f"{divider}\n"
        f"Placement Registry Authentication Token: NH-OFF-{offer.id:06d}-SECURE\n"
        f"{divider}\n"
    )

    response = HttpResponse(body, content_type='text/plain')
    filename = f"NH_Offer_{offer.company.company_name.replace(' ', '_')}_{offer.trainee.batch_code}.txt"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
def application_resume_preview_view(req, app_id):
    """
    Returns the specific resume uploaded for this job application.
    """
    from django.core.exceptions import PermissionDenied
    from django.http import Http404, FileResponse
    
    app = get_object_or_454(Application, id=app_id)
    user = req.user
    
    if user.profile.role == Role.TRAINEE and app.trainee.user != user:
        raise PermissionDenied("You do not have permission to view this resume.")
    elif user.profile.role == Role.RECRUITER and app.job.recruiter.user != user:
        raise PermissionDenied("You do not have permission to view this resume.")
        
    if not app.resume or not app.resume.resume_file:
        if app.trainee.resume_file:
            return FileResponse(app.trainee.resume_file.open('rb'), content_type='application/pdf')
        raise Http404("No resume found for this application.")
        
    return FileResponse(app.resume.resume_file.open('rb'), content_type='application/pdf')
