# trainees/views.py
"""
Student candidate views controllers.
Implements dashboards, profile editing, resume lifecycles (upload, update, delete, stream), 
and advanced custom statistics analytics.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.http import FileResponse, Http404, HttpResponseForbidden
from .models import TraineeProfile, Resume
from .forms import StudentProfileForm, ResumeForm
from accounts.models import Role
from jobs.models import Job
from applications.models import Application, Status
from notifications.models import Notification
import os

# RBAC Gating Decorator helper
def is_authorized_student(user):
    """
    Enforces authorization check. Only authenticated users with STUDENT role
    or superusers are allowed access. Unauthorised users are routed back to Login.
    """
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.role == 'admin':
        return True
    if user.role != Role.TRAINEE:
        return False
    try:
        return user.trainee_profile.approval_status == 'approved'
    except TraineeProfile.DoesNotExist:
        return False

@login_required
@user_passes_test(is_authorized_student, login_url='accounts:login')
def trainee_dashboard_view(req):
    """
    Phase 2 & 5 - Complete Student Control Dashboard & Analytics Panel.
    Compiles placement pipelines, active recommendations, notifications, and analytics trackers.
    """
    trainee = get_object_or_404(TraineeProfile, user=req.user)
    
    # 1. Pipeline Counter Metrics
    applications = trainee.applications.select_related('job', 'job__recruiter').all()
    applied_count = applications.count()
    shortlisted_count = applications.filter(status='SHORTLISTED').count()
    
    # Track scheduled interviews via linked applications
    interviews_list = []
    for app in applications:
        for interview in app.interviews.filter(status='SCHEDULED'):
            interviews_list.append(interview)
    interviews_count = len(interviews_list)
    
    offers_count = applications.filter(status__in=[Status.OFFER_EXTENDED, Status.OFFER_ACCEPTED]).count()

    # 2. Recommended Positions Engine
    # Matches active jobs where trainee CGPA >= required, trainee course matches job required_courses, and overlaps at least 1 skill if skills exist
    rec_jobs = Job.objects.filter(is_active=True, min_cgpa_required__lte=trainee.cgpa).prefetch_related('required_courses')
    student_courses = set(trainee.courses.values_list('id', flat=True))
    matched_jobs = []
    for job in rec_jobs:
        job_course_ids = set(job.required_courses.values_list('id', flat=True))
        if job_course_ids and not job_course_ids.intersection(student_courses):
            continue  # Course mismatch
            
        # Check skill similarities or generic relevance matches
        job_skills = set(job.skills_required) if isinstance(job.skills_required, list) else set()
        user_skills = set(trainee.skills) if isinstance(trainee.skills, list) else set()
        
        # If trainee has skills, check intersection, else show general matches
        if not user_skills or job_skills.intersection(user_skills):
            matched_jobs.append(job)
            
    # Limit recommendation items
    recommended_jobs = matched_jobs[:4]

    # 3. Dynamic Activity Stream Logging
    recent_activities = []
    # Log application submittals
    for app in applications[:5]:
        recent_activities.append({
            'type': 'application',
            'title': f"Applied for {app.job.title}",
            'subtitle': app.job.recruiter.company_name,
            'timestamp': app.applied_at,
            'status': app.get_status_display(),
            'color': 'text-blue-400' if app.status == 'PENDING' else 'text-emerald-400'
        })
    # Log scheduled interviews
    for interview in interviews_list[:5]:
        recent_activities.append({
            'type': 'interview',
            'title': f"Interview: {interview.title}",
            'subtitle': f"{interview.platform} | stage: {interview.get_stage_display()}",
            'timestamp': interview.scheduled_at,
            'status': interview.get_status_display(),
            'color': 'text-amber-400'
        })
    
    # Sort activities by timestamp descending
    recent_activities.sort(key=lambda x: x['timestamp'], reverse=True)
    recent_activities = recent_activities[:6]

    # 4. In-App Notifications
    unread_notifications = req.user.notifications.filter(is_read=False)[:5]
    all_notifications_count = req.user.notifications.filter(is_read=False).count()
    recommendations = trainee.placement_recommendations.select_related('job', 'job__recruiter', 'recommended_by')

    # Compile set of job IDs that trainee has already applied to
    applied_job_ids = set(applications.values_list('job_id', flat=True))

    # Calculate eligibility lists for dashboard jobs
    course_eligible_job_ids = []
    experience_eligible_job_ids = []
    student_courses_list = list(trainee.courses.values_list('id', flat=True))
    for job in recommended_jobs:
        job_required_course_ids = list(job.required_courses.values_list('id', flat=True))
        if not job_required_course_ids or any(c_id in student_courses_list for c_id in job_required_course_ids):
            course_eligible_job_ids.append(job.id)
        if trainee.experience_years >= job.experience_required:
            experience_eligible_job_ids.append(job.id)

    context = {
        'trainee': trainee,
        'profile_completion': trainee.profile_completion_percentage,
        'readiness_score': trainee.placement_readiness_score,
        
        # Pipeline metric lists
        'applied_count': applied_count,
        'shortlisted_count': shortlisted_count,
        'interviews_count': interviews_count,
        'offers_count': offers_count,
        
        # Lists
        'applications': applications,
        'recommended_jobs': recommended_jobs,
        'applied_job_ids': applied_job_ids,
        'course_eligible_job_ids': course_eligible_job_ids,
        'experience_eligible_job_ids': experience_eligible_job_ids,
        'recent_activities': recent_activities,
        'notifications': unread_notifications,
        'unread_count': all_notifications_count,
        'recommendations': recommendations,
    }
    return render(req, 'trainee/dashboard.html', context)


@login_required
@user_passes_test(is_authorized_student, login_url='accounts:login')
def trainee_profile_edit_view(req):
    """
    Phase 3 - Personal, Academic & Professional Profile Configuration.
    Processes name records, photo avatars, degree domains, certifications, and internships.
    """
    trainee = get_object_or_404(TraineeProfile, user=req.user)
    
    if req.method == 'POST':
        form = StudentProfileForm(req.POST, req.FILES, instance=trainee)
        if form.is_valid():
            profile = form.save(commit=False)
            
            # Extract Course Completion Statuses
            from accounts.models import Course
            completion = {}
            for course in Course.objects.all():
                status_val = req.POST.get(f'course_status_{course.id}')
                if status_val:
                    completion[course.name] = status_val
            profile.course_completion = completion
            
            # Extract Certifications
            certifications = []
            if req.POST.get('has_certifications') == 'yes':
                names = req.POST.getlist('cert_name[]')
                orgs = req.POST.getlist('cert_org[]')
                dates = req.POST.getlist('cert_date[]')
                urls = req.POST.getlist('cert_url[]')
                for n, o, d, u in zip(names, orgs, dates, urls):
                    if n.strip() or o.strip():
                        certifications.append({
                            'name': n.strip(),
                            'organization': o.strip(),
                            'issue_date': d.strip(),
                            'credential_url': u.strip()
                        })
            profile.certifications = certifications
            
            # Extract Internships
            internships = []
            if req.POST.get('has_internships') == 'yes':
                companies = req.POST.getlist('intern_company[]')
                roles = req.POST.getlist('intern_role[]')
                durations = req.POST.getlist('intern_duration[]')
                descs = req.POST.getlist('intern_desc[]')
                for c, r, du, de in zip(companies, roles, durations, descs):
                    if c.strip() or r.strip():
                        internships.append({
                            'company': c.strip(),
                            'role': r.strip(),
                            'duration': du.strip(),
                            'description': de.strip()
                        })
            profile.internships = internships
            
            # Extract Projects
            projects = []
            if req.POST.get('has_projects') == 'yes':
                names = req.POST.getlist('proj_name[]')
                techs = req.POST.getlist('proj_tech[]')
                descs = req.POST.getlist('proj_desc[]')
                links = req.POST.getlist('proj_link[]')
                for n, t, de, li in zip(names, techs, descs, links):
                    if n.strip():
                        projects.append({
                            'name': n.strip(),
                            'technologies': t.strip(),
                            'description': de.strip(),
                            'github_link': li.strip()
                        })
            profile.projects = projects
            
            profile.save()
            form.save_m2m()
            messages.success(req, "Congratulations! Your NextHire profile has been fully updated.")
            return redirect('trainees:profile')
        else:
            messages.error(req, "Validation error! Please review form entries for discrepancies.")
    else:
        form = StudentProfileForm(instance=trainee)
        
    return render(req, 'trainee/profile.html', {
        'form': form, 
        'trainee': trainee,
        'profile_completion': trainee.profile_completion_percentage
    })


@login_required
@user_passes_test(is_authorized_student, login_url='accounts:login')
def resume_management_view(req):
    """
    Phase 4 - Resume Document Lifecycle Desk.
    Renders the central upload terminal, formats checker, and listings metadata.
    """
    trainee = get_object_or_404(TraineeProfile, user=req.user)
    
    if req.method == 'POST':
        form = ResumeForm(req.POST, req.FILES, instance=trainee)
        if form.is_valid():
            profile_instance = form.save(commit=False)
            profile_instance.resume_uploaded_at = timezone.now()
            profile_instance.save()
            
            # Sync with the new Resume model
            Resume.objects.update_or_create(
                trainee=trainee,
                defaults={
                    'resume_file': profile_instance.resume_file,
                    'is_active': True
                }
            )
            
            messages.success(req, "Pristine file successfully loaded! Resume is now cached for recruiting feeds screening.")
            return redirect('trainees:resume')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(req, f"File rejected: {error}")
    else:
        form = ResumeForm(instance=trainee)
        
    return render(req, 'trainee/resume.html', {
        'form': form,
        'trainee': trainee
    })


@login_required
@user_passes_test(is_authorized_student, login_url='accounts:login')
def resume_delete_view(req):
    """
    Phase 4 - Deletes trainee resume file from local container storage safely on request.
    """
    trainee = get_object_or_404(TraineeProfile, user=req.user)
    
    if trainee.resume_file:
        try:
            # Physical disk deletion logic wrapper
            if os.path.isfile(trainee.resume_file.path):
                os.remove(trainee.resume_file.path)
            
            # Reset database pointers
            trainee.resume_file = None
            trainee.resume_uploaded_at = None
            trainee.save()
            
            # Sync with the new Resume model by deleting its record
            Resume.objects.filter(trainee=trainee).delete()
            
            messages.warning(req, "Doc reference deleted. Please upload an updated resume to avoid placement disqualifications.")
        except Exception as e:
            messages.error(req, f"An unexpected storage discrepancy occurred during file deletion: {str(e)}")
            
    return redirect('trainees:resume')


@login_required
def resume_preview_view(req, usn):
    """
    Phase 4 - Streams cached PDF/DOCX resumes safely with custom content attachment headers.
    Ensures safe authorization so that recruiters or candidate owners can view documents.
    """
    trainee = get_object_or_404(TraineeProfile, usn=usn)
    
    # Security Authorization access guard:
    # Allow document streaming only for the owner trainee, staff admins, or recruiting corporate partners.
    is_owner = (req.user == trainee.user)
    is_admin = req.user.is_superuser or req.user.is_staff
    is_recruiter = (req.user.profile.role == Role.RECRUITER) if hasattr(req.user, 'profile') else False
    
    if not (is_owner or is_admin or is_recruiter):
        return HttpResponseForbidden("Unauthorized Document Access: You details are not accredited to audit this resume.")

    if not trainee.resume_file:
         raise Http404("Document Not Discovered: No verified resume uploaded for this USN yet.")
         
    try:
        # Determine appropriate content types
        file_path = trainee.resume_file.path
        extension = os.path.splitext(file_path)[1].lower()
        
        if extension == '.pdf':
            content_type = 'application/pdf'
        elif extension == '.docx':
            content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        else:
            content_type = 'application/octet-stream'
            
        return FileResponse(open(file_path, 'rb'), content_type=content_type)
    except FileNotFoundError:
        raise Http404("Document Missing: File not found in database container registry volume.")


@login_required
@user_passes_test(is_authorized_student, login_url='accounts:login')
def trainee_analytics_view(req):
    """
    Phase 5 - Student Performance Charts & Preparedness Cockpit.
    Compiles detailed evaluations vectors including GPA gaps, placement predictions, and mock ranks.
    """
    from interviews.models import Interview
    trainee = get_object_or_404(TraineeProfile, user=req.user)
    applications = trainee.applications.all()
    
    # Calculate detailed performance ratings
    gpa_gap = round(float(10.00 - float(trainee.cgpa)), 2)
    
    # Group counts as per the 2nd screenshot layout:
    # 1. Under Review: PENDING + TESTING
    # 2. Shortlisted: SHORTLISTED
    # 3. Interviews: INTERVIEWING
    # 4. Offers: OFFER_EXTENDED + OFFER_ACCEPTED
    # 5. Rejected: REJECTED
    under_review = applications.filter(status__in=[Status.PENDING, Status.TESTING]).count()
    shortlisted = applications.filter(status=Status.SHORTLISTED).count()
    interviews = applications.filter(status=Status.INTERVIEWING).count()
    offers = applications.filter(status__in=[Status.OFFER_EXTENDED, Status.OFFER_ACCEPTED]).count()
    rejected = applications.filter(status=Status.REJECTED).count()
    
    total = under_review + shortlisted + interviews + offers + rejected
    
    # Calculate dynamic conic gradient style for the pie chart
    conic_segments = []
    current_deg = 0
    colors = {
        'under_review': '#3b82f6', # blue
        'shortlisted': '#06b6d4',  # cyan
        'interviews': '#f59e0b',   # orange
        'offers': '#10b981',       # green
        'rejected': '#ef4444',     # red
    }
    
    if total == 0:
        conic_style = "background: #475569;"  # solid grey if no records
    else:
        if under_review > 0:
            deg = (under_review / total) * 360
            conic_segments.append(f"{colors['under_review']} {current_deg}deg {current_deg + deg}deg")
            current_deg += deg
        if shortlisted > 0:
            deg = (shortlisted / total) * 360
            conic_segments.append(f"{colors['shortlisted']} {current_deg}deg {current_deg + deg}deg")
            current_deg += deg
        if interviews > 0:
            deg = (interviews / total) * 360
            conic_segments.append(f"{colors['interviews']} {current_deg}deg {current_deg + deg}deg")
            current_deg += deg
        if offers > 0:
            deg = (offers / total) * 360
            conic_segments.append(f"{colors['offers']} {current_deg}deg {current_deg + deg}deg")
            current_deg += deg
        if rejected > 0:
            deg = (rejected / total) * 360
            conic_segments.append(f"{colors['rejected']} {current_deg}deg {current_deg + deg}deg")
            current_deg += deg
        conic_style = f"background: conic-gradient({', '.join(conic_segments)});"

    # Retrieve completed interviews rating scores for the trend chart
    completed_interviews = Interview.objects.filter(
        application__trainee=trainee
    ).exclude(status=Interview.Status.SCHEDULED).order_by('scheduled_at')
    
    context = {
        'trainee': trainee,
        'profile_completion': trainee.profile_completion_percentage,
        'readiness': trainee.placement_readiness_score,
        'gpa_gap': gpa_gap,
        'total_apps': total,
        
        # Pipeline counts
        'under_review_count': under_review,
        'shortlisted_count': shortlisted,
        'interviews_count': interviews,
        'offers_count': offers,
        'rejected_count': rejected,
        
        # Pie chart gradient
        'conic_style': conic_style,
        'completed_interviews': completed_interviews,
    }
    return render(req, 'trainee/analytics.html', context)


@login_required
@user_passes_test(is_authorized_student, login_url='accounts:login')
def trainee_prediction_view(req):
    """
    Placement Prediction view.
    Loads trainee profile features, invokes RandomForest classifier,
    and renders prediction results and placement readiness reports.
    """
    trainee = get_object_or_404(TraineeProfile, user=req.user)
    
    # Import predict helper
    from predict import predict_for_student
    
    # Run prediction based on trainee profile
    probability, prediction_result = predict_for_student(trainee)
    prob_percentage = round(probability * 100, 1)
    
    # Determine readiness status based on probability
    if probability >= 0.75:
        readiness_status = "Excellent - Highly Prepared"
        status_color = "emerald"
    elif probability >= 0.50:
        readiness_status = "Good - Moderately Prepared"
        status_color = "amber"
    else:
        readiness_status = "Needs Improvement - Potential Risk"
        status_color = "rose"
        
    context = {
        'trainee': trainee,
        'probability': prob_percentage,
        'prediction_result': prediction_result,
        'readiness_status': readiness_status,
        'status_color': status_color,
    }
    return render(req, 'trainee/prediction.html', context)


@login_required
@user_passes_test(is_authorized_student, login_url='accounts:login')
def student_resume_analysis_view(req):
    """
    AI Resume Analyzer view.
    Uploads a resume PDF, extracts text via PyMuPDF, invokes Gemini API metrics,
    and returns a structured score, missing skills list, and improvement tips suggestions.
    """
    trainee = get_object_or_404(TraineeProfile, user=req.user)
    results = None
    
    if req.method == 'POST' and req.FILES.get('resume_file'):
        resume_file = req.FILES['resume_file']
        
        if not resume_file.name.lower().endswith('.pdf'):
            messages.error(req, "Please upload a valid PDF document.")
            return redirect('trainees:resume_analysis')
            
        try:
            import fitz  # PyMuPDF
            file_bytes = resume_file.read()
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            extracted_text = ""
            for page in doc:
                extracted_text += page.get_text()
                
            if not extracted_text.strip():
                messages.error(req, "Could not extract readable text from the uploaded PDF. Make sure it contains text rather than scanned images.")
                return redirect('trainees:resume_analysis')
                
            # Send to Gemini
            from ai_helpers import analyze_resume
            results = analyze_resume(extracted_text)
            
            # Sync trainee placement readiness scorecard
            trainee.placement_readiness_score = int((trainee.placement_readiness_score + results['resume_score']) / 2)
            trainee.save()
            
            messages.success(req, "AI Resume Analysis completed successfully!")
        except Exception as e:
            messages.error(req, f"Resume diagnostics failure: {e}")
            
    return render(req, 'trainee/resume_analysis.html', {
        'trainee': trainee,
        'results': results
    })


@login_required
@user_passes_test(is_authorized_student, login_url='accounts:login')
def student_interview_view(req):
    """
    AI Mock Interview simulation view.
    Conducts a 3-round technical assessment tracked inside the Django session,
    evaluating performance with score and feedback outputs.
    """
    trainee = get_object_or_404(TraineeProfile, user=req.user)
    step = req.session.get('interview_step', 0)
    
    if step == 0:
        if req.method == 'POST':
            role = req.POST.get('role_title', '').strip()
            if not role:
                messages.error(req, "Please select a target career role.")
                return redirect('trainees:interview')
                
            req.session['interview_role'] = role
            req.session['interview_step'] = 1
            req.session['interview_questions'] = []
            req.session['interview_answers'] = []
            req.session['interview_scores'] = []
            req.session['interview_feedbacks'] = []
            
            from ai_helpers import generate_mock_interview_question
            q = generate_mock_interview_question(role)
            req.session['interview_questions'].append(q)
            req.session.modified = True
            return redirect('trainees:interview')
            
        return render(req, 'trainee/interview.html', {
            'step': 0,
            'trainee': trainee
        })
        
    elif step in [1, 2, 3]:
        questions = req.session.get('interview_questions', [])
        current_question = questions[-1] if questions else "Can you explain middleware in web applications?"
        
        if req.method == 'POST':
            answer = req.POST.get('answer', '').strip()
            if not answer:
                messages.error(req, "Please write your answer.")
                return redirect('trainees:interview')
                
            role = req.session.get('interview_role')
            
            from ai_helpers import evaluate_mock_interview_answer
            evaluation = evaluate_mock_interview_answer(role, current_question, answer)
            
            req.session['interview_answers'].append(answer)
            req.session['interview_scores'].append(evaluation['score'])
            req.session['interview_feedbacks'].append(evaluation['feedback'])
            
            next_step = step + 1
            req.session['interview_step'] = next_step
            
            if next_step <= 3:
                from ai_helpers import generate_mock_interview_question
                history = ""
                for idx, q_text in enumerate(questions):
                    a_text = req.session['interview_answers'][idx]
                    history += f"Q: {q_text}\nA: {a_text}\n"
                q = generate_mock_interview_question(role, history)
                req.session['interview_questions'].append(q)
            else:
                scores = req.session.get('interview_scores', [])
                if scores:
                    avg_score = int(sum(scores) / len(scores))
                    trainee.placement_readiness_score = int((trainee.placement_readiness_score + avg_score) / 2)
                    trainee.save()
            
            req.session.modified = True
            return redirect('trainees:interview')
            
        return render(req, 'trainee/interview.html', {
            'step': step,
            'question': current_question,
            'role': req.session.get('interview_role'),
            'trainee': trainee
        })
        
    else:
        role = req.session.get('interview_role')
        questions = req.session.get('interview_questions', [])
        answers = req.session.get('interview_answers', [])
        scores = req.session.get('interview_scores', [])
        feedbacks = req.session.get('interview_feedbacks', [])
        
        avg_score = int(sum(scores) / len(scores)) if scores else 0
        
        if req.method == 'POST' and req.POST.get('action') == 'reset':
            req.session['interview_step'] = 0
            req.session.modified = True
            return redirect('trainees:interview')
            
        interview_history = zip(questions, answers, scores, feedbacks)
        
        return render(req, 'trainee/interview.html', {
            'step': 4,
            'role': role,
            'avg_score': avg_score,
            'interview_history': interview_history,
            'trainee': trainee
        })


@login_required
@user_passes_test(is_authorized_student, login_url='accounts:login')
def student_chatbot_view(req):
    """
    AI Career Assistant chatbot view.
    Engages in dialogue regarding career choices, upskilling, and placement roadmap options.
    """
    trainee = get_object_or_404(TraineeProfile, user=req.user)
    chat_history = req.session.get('student_chat_history', [])
    
    if req.method == 'POST':
        query = req.POST.get('query', '').strip()
        action = req.POST.get('action', '')
        
        if action == 'clear':
            req.session['student_chat_history'] = []
            req.session.modified = True
            return redirect('trainees:chatbot')
            
        if query:
            chat_history.append({'role': 'user', 'content': query})
            
            history_str = ""
            for msg in chat_history[-10:]:
                history_str += f"{'Student' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}\n"
                
            from ai_helpers import get_career_guidance
            reply = get_career_guidance(trainee, query, history_str)
            
            chat_history.append({'role': 'ai', 'content': reply})
            
            req.session['student_chat_history'] = chat_history
            req.session.modified = True
            return redirect('trainees:chatbot')
            
    if not chat_history:
        greeting = (
            f"Hello {req.user.get_full_name() or req.user.email}! "
            "I am your personal NextHire AI Career Assistant. "
            "Ask me anything about career options, what technical skills to acquire, or which job fits you best!"
        )
        chat_history.append({'role': 'ai', 'content': greeting})
        req.session['student_chat_history'] = chat_history
        req.session.modified = True
        
    return render(req, 'trainee/chatbot.html', {
        'trainee': trainee,
        'chat_messages': chat_history
    })


def is_student_or_pending(user):
    return user.is_authenticated and (user.is_superuser or user.role == 'admin' or user.role == Role.TRAINEE)

@login_required
@user_passes_test(is_student_or_pending, login_url='accounts:login')
def trainee_course_details_view(req):
    """
    Renders and processes trainee Course Details page.
    """
    trainee = get_object_or_404(TraineeProfile, user=req.user)
    from accounts.models import Course
    
    if req.method == 'POST':
        batch_code = req.POST.get('batch_code', '').strip()
        selected_course_ids = req.POST.getlist('courses')
        selected_course_set = {int(cid) for cid in selected_course_ids if cid.isdigit()}
        current_course_set = {c.id for c in trainee.courses.all()}
        
        batch_code_changed = (batch_code != (trainee.batch_code or ''))
        courses_changed = (selected_course_set != current_course_set)
        
        if batch_code_changed or courses_changed:
            if batch_code:
                trainee.batch_code = batch_code
            trainee.courses.set(list(selected_course_set))
            # Set to pending approval
            trainee.approval_status = 'pending'
            trainee.course_edit_request_status = 'pending'
            trainee.is_course_editable = False
            
            # Save other fields as well
            trainee.batch_timing = req.POST.get('batch_timing', '')
            joining_date = req.POST.get('joining_date', '')
            trainee.joining_date = joining_date if joining_date else None
            expected_completion_date = req.POST.get('expected_completion_date', '')
            trainee.expected_completion_date = expected_completion_date if expected_completion_date else None
            trainee.current_status = req.POST.get('current_status', 'Training')
            
            completion = {}
            for course in Course.objects.all():
                status_val = req.POST.get(f'course_status_{course.id}')
                if status_val:
                    completion[course.name] = status_val
            trainee.course_completion = completion
            
            trainee.save()
            messages.success(req, "Your batch code/course changes have been saved and submitted for approval. You must wait for verification to access dashboard features.")
            return redirect('accounts:role_routing')
        else:
            # Update other fields that do not require approval
            trainee.batch_timing = req.POST.get('batch_timing', '')
            joining_date = req.POST.get('joining_date', '')
            trainee.joining_date = joining_date if joining_date else None
            expected_completion_date = req.POST.get('expected_completion_date', '')
            trainee.expected_completion_date = expected_completion_date if expected_completion_date else None
            trainee.current_status = req.POST.get('current_status', 'Training')
            
            completion = {}
            for course in Course.objects.all():
                status_val = req.POST.get(f'course_status_{course.id}')
                if status_val:
                    completion[course.name] = status_val
            trainee.course_completion = completion
            
            trainee.save()
            messages.success(req, "Course details successfully updated.")
            return redirect('trainees:course_details')
            
    all_courses = Course.objects.all()

    context = {
        'trainee': trainee,
        'all_courses': all_courses,
        'course_completion': trainee.course_completion,
    }
    return render(req, 'trainee/course.html', context)


@login_required
@user_passes_test(is_authorized_student, login_url='accounts:login')
def trainee_course_request_edit_view(req):
    """
    Submits a pending request to edit batch code & courses enrolled.
    """
    trainee = get_object_or_404(TraineeProfile, user=req.user)
    if trainee.course_edit_request_status in ('none', 'rejected'):
        trainee.course_edit_request_status = 'pending'
        trainee.save()
        messages.success(req, "Request for editing Batch Code and Enrolled Courses has been submitted successfully.")
    return redirect('trainees:course_details')



