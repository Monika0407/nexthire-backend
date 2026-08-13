# django_backend/ai/views.py
"""
AI Suite View Controllers.
Coordinates resume parsing, mock technical interview cycles, career advisor chatbot, 
and prompt administration utilities. Handled with strict RBAC clearances.
"""

import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponseForbidden, JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Avg

from accounts.models import Role, UserProfile
from accounts.models import TraineeProfile
from jobs.models import Job
from .models import (
    PromptTemplate, ResumeAnalysis, ResumeRoadmap, 
    InterviewSession, InterviewMessage, CareerGuidanceSession, CareerGuidanceMessage
)
from .services import GeminiService
from .decorators import student_required, recruiter_required, admin_required

# Helper to build a comprehensive candidate index text for Gemini context
def _build_candidate_context_text(profile: TraineeProfile):
    """
    Assembles a robust textual profile summarizing candidate achievements 
    to parse into Gemini safely when binary resume parsing is unavailable.
    """
    skills_str = ", ".join(profile.skills) if isinstance(profile.skills, list) else str(profile.skills)
    certs_str = ", ".join(profile.certifications) if isinstance(profile.certifications, list) else str(profile.certifications)
    intern_str = ""
    if isinstance(profile.internships, list):
        for i, intern in enumerate(profile.internships, 1):
            if isinstance(intern, dict):
                intern_str += f"\n- Internship {i}: {intern.get('role','Intern')} at {intern.get('company','Company')} ({intern.get('duration','N/A')})"
            else:
                intern_str += f"\n- Internship {i}: {intern}"
    else:
        intern_str = str(profile.internships)

    context_text = (
        f"Batch Code: {profile.batch_code}\n"
        f"Degree: {profile.get_degree_display()}\n"
        f"Branch specialization: {profile.branch}\n"
        f"Cumulative CGPA: {profile.cgpa} / 10.0\n"
        f"Listed Core Skills: {skills_str}\n"
        f"Acquired Certifications: {certs_str}\n"
        f"Professional Internship Records: {intern_str}\n"
    )

    # Append any text from uploaded file if readable (simple text file reader for basic support)
    if profile.resume_file:
        try:
            profile.resume_file.open('r')
            file_text = profile.resume_file.read(5000) # read up to 5000 characters
            profile.resume_file.close()
            if isinstance(file_text, bytes):
                file_text = file_text.decode('utf-8', errors='ignore')
            context_text += f"\nUploaded CV Metadata Text Contents:\n{file_text}"
        except Exception:
            pass # resilient bypass if binary PDF or permissions block direct reading

    return context_text


def ai_dashboard(request):
    """
    Phase 6 & 8 Dynamic AI Analytics Insights & History Ledger.
    Calculates composite readiness cards, displays score graphs, and aggregates historical logs.
    """
    if not request.user.is_authenticated:
        return redirect('accounts:login')

    user_role = request.user.profile.role

    if user_role == Role.TRAINEE:
        if not hasattr(request.user, 'trainee_profile'):
            messages.warning(request, "Please set up your trainee profile profile first.")
            return redirect('trainees:edit_profile')

        trainee = request.user.trainee_profile
        
        # Pull past evaluations
        analyses = ResumeAnalysis.objects.filter(trainee=trainee)
        roadmaps = ResumeRoadmap.objects.filter(trainee=trainee)
        interviews = InterviewSession.objects.filter(trainee=trainee)
        
        latest_analysis = analyses.first()
        latest_roadmap = roadmaps.first()
        
        # Compute dynamic scores
        resume_readiness = latest_analysis.resume_score if latest_analysis else 70
        
        # Completed mock interviews average score
        completed_interviews = interviews.filter(is_completed=True)
        if completed_interviews.exists():
            avg_tech = completed_interviews.aggregate(Avg('technical_score'))['technical_score__avg'] or 75
            avg_comm = completed_interviews.aggregate(Avg('communication_score'))['communication_score__avg'] or 75
            interview_readiness = int((avg_tech + avg_comm) / 2)
        else:
            interview_readiness = 70 # baseline starting

        career_readiness = int((resume_readiness + interview_readiness + int(trainee.placement_readiness_score)) / 3)

        # Sparklines / Trends Mock Dataset
        trends = [
            {"label": "Resume", "val": resume_readiness},
            {"label": "Mock Q&A", "val": interview_readiness},
            {"label": "Profile", "val": int(trainee.placement_readiness_score)},
            {"label": "Overall", "val": career_readiness}
        ]

        # Recent activities log
        recent_guidance = CareerGuidanceSession.objects.filter(trainee=trainee)[:3]

        context = {
            'role': 'STUDENT',
            'trainee': trainee,
            'latest_analysis': latest_analysis,
            'latest_roadmap': latest_roadmap,
            'analyses_history': analyses[:5],
            'interviews_history': interviews[:5],
            'recent_guidance': recent_guidance,
            # Phase 6 Readiness Cards
            'resume_readiness': resume_readiness,
            'interview_readiness': interview_readiness,
            'career_readiness': career_readiness,
            'trends': trends,
        }
        return render(request, 'ai/dashboard.html', context)

    # For Recruiter and Administrators - general aggregation stats
    elif user_role == Role.RECRUITER or user_role == Role.ADMIN:
        total_analyses = ResumeAnalysis.objects.count()
        total_interviews = InterviewSession.objects.count()
        avg_resume_score = ResumeAnalysis.objects.aggregate(Avg('resume_score'))['resume_score__avg'] or 75
        avg_interview_score = InterviewSession.objects.filter(is_completed=True).aggregate(
            avg_score=Avg((Avg('technical_score') + Avg('communication_score')) / 2)
        )['avg_score'] or 72

        if user_role == Role.RECRUITER:
            top_candidates = TraineeProfile.objects.filter(approval_status='approved').order_by('-placement_readiness_score')[:5]
        else:
            top_candidates = TraineeProfile.objects.all().order_by('-placement_readiness_score')[:5]

        context = {
            'role': user_role,
            'total_analyses': total_analyses,
            'total_interviews': total_interviews,
            'avg_resume_score': int(avg_resume_score),
            'avg_interview_score': int(avg_interview_score) if avg_interview_score else 72,
            'top_candidates': top_candidates,
            'is_admin': user_role == Role.ADMIN
        }
        return render(request, 'ai/dashboard_comm.html', context)

    return redirect('accounts:login')


@student_required
def resume_analyze(request):
    """
    Phase 2 Resume Intelligence trigger.
    Pipes trainee records into LLM parsing matrix, updating composite scorecard.
    """
    trainee = request.user.trainee_profile
    
    # Assert trainee has registered skills or general file
    candidate_text = _build_candidate_context_text(trainee)
    
    # Notify processing
    messages.info(request, "Transmitting profile details to NextHire AI Analyzer...")
    
    # Make call
    report = GeminiService.analyze_resume(candidate_text)
    
    # Extract results
    score = report.get("resume_score", 70)
    summary = report.get("resume_summary", "Profile evaluation completed.")
    missing = report.get("missing_skills", [])
    tips = report.get("improvement_tips", [])

    # Save details
    analysis = ResumeAnalysis.objects.create(
        trainee=trainee,
        resume_score=score,
        resume_summary=summary,
        missing_skills=missing,
        improvement_tips=tips
    )

    # Sync candidate's placement readiness scorecard index
    trainee.placement_readiness_score = int((trainee.placement_readiness_score + score) / 2)
    trainee.save()

    messages.success(request, f"Review completed successfully! Profile Evaluation Score: {score}%")
    return redirect('ai:dashboard')


@student_required
def resume_roadmap(request):
    """
    Phase 5 Comprehensive Resume Improvement Roadmap pipeline.
    """
    trainee = request.user.trainee_profile
    roadmap = ResumeRoadmap.objects.filter(trainee=trainee).first()

    if not roadmap or 'regenerate' in request.GET:
        # Build new roadmap
        candidate_text = _build_candidate_context_text(trainee)
        messages.info(request, "Compiling personalized CV upgrade roadmap...")
        
        data = GeminiService.generate_roadmap(trainee, candidate_text)
        
        # Save record
        if roadmap:
            roadmap.weak_areas = data.get("weak_areas", [])
            roadmap.recommendations = data.get("recommendations", [])
            roadmap.target_resume_suggestions = data.get("target_resume_suggestions", "")
            roadmap.save()
        else:
            roadmap = ResumeRoadmap.objects.create(
                trainee=trainee,
                weak_areas=data.get("weak_areas", []),
                recommendations=data.get("recommendations", []),
                target_resume_suggestions=data.get("target_resume_suggestions", ""),
                progress_percentage=10
            )
        messages.success(request, "Fresh CV Upgrade Roadmap created!")

    context = {
        'trainee': trainee,
        'roadmap': roadmap,
    }
    return render(request, 'ai/roadmap.html', context)


@student_required
@require_POST
def update_roadmap_progress(request):
    """
    Saves candidate progress checklist ticks.
    """
    trainee = request.user.trainee_profile
    roadmap = get_object_or_404(ResumeRoadmap, trainee=trainee)
    
    try:
        progress = int(request.POST.get('progress_percentage', roadmap.progress_percentage))
        roadmap.progress_percentage = max(0, min(100, progress))
        roadmap.save()
        messages.success(request, f"Roadmap progress coordinates updated to {roadmap.progress_percentage}%")
    except ValueError:
        messages.error(request, "Failed to parse index.")

    return redirect('ai:resume_roadmap')


@student_required
def interview_list(request):
    """
    Mock Interview Home view. Lets trainee start or review practice sessions.
    """
    trainee = request.user.trainee_profile
    sessions = InterviewSession.objects.filter(trainee=trainee)
    all_jobs = Job.objects.filter(is_active=True)

    context = {
        'sessions': sessions,
        'all_jobs': all_jobs,
    }
    return render(request, 'ai/interview_list.html', context)


@student_required
@require_POST
def interview_start(request):
    """
    Initializes a fresh technical mock interview.
    """
    trainee = request.user.trainee_profile
    role_title = request.POST.get('role_title', '').strip()
    job_id = request.POST.get('job_id')
    
    selected_job = None
    job_desc = "Standard Technical Position description"
    skills_list = trainee.skills

    if job_id:
        selected_job = get_object_or_404(Job, id=job_id)
        role_title = selected_job.title
        job_desc = selected_job.description
        skills_list = selected_job.skills_required

    if not role_title:
        role_title = "Full-Stack Software Engineer"

    # Create session
    session = InterviewSession.objects.create(
        trainee=trainee,
        job=selected_job,
        role_title=role_title,
        current_question_index=1
    )

    # Query first question from LLM
    first_question = GeminiService.get_next_question(
        role_title=role_title,
        job_desc=job_desc,
        skills_list=skills_list,
        dialog_history_str="[SYSTEM]: Start Session. Prompt first technical challenge question."
    )

    # Save message
    InterviewMessage.objects.create(
        session=session,
        role='ai',
        content=first_question
    )

    messages.success(request, f"Successfully spun up {role_title} Mock Session!")
    return redirect('ai:interview_session', session_id=session.id)


@student_required
def interview_session(request, session_id):
    """
    Active Interview dialog panel. Renders dialog blocks, formats code.
    """
    trainee = request.user.trainee_profile
    session = get_object_or_404(InterviewSession, id=session_id, trainee=trainee)
    all_messages = session.messages.all()

    if request.method == 'POST' and not session.is_completed:
        answer = request.POST.get('answer', '').strip()
        if not answer:
            messages.warning(request, "Answer content cannot be blank.")
            return redirect('ai:interview_session', session_id=session.id)

        # 1. Save trainee response
        InterviewMessage.objects.create(
            session=session,
            role='trainee',
            content=answer
        )

        # Check total answer cycle count
        student_msgs = all_messages.filter(role='trainee')
        round_count = student_msgs.count() + 1 # include the current one to submit

        if round_count >= 3: # 3-round compact cycle
            session.is_completed = True
            session.save()

            messages.info(request, "Assembling dialogue transcripts for performance evaluation...")

            # Calculate evaluations
            dialogue_str = ""
            for m in session.messages.all():
                role_label = "Student" if m.role == 'trainee' else "AI Interviewer"
                dialogue_str += f"{role_label}: {m.content}\n\n"

            eval_report = GeminiService.evaluate_interview(session.role_title, dialogue_str)

            session.technical_score = eval_report.get("technical_score", 75)
            session.communication_score = eval_report.get("communication_score", 80)
            session.suggestions = eval_report.get("suggestions", "Good presentation values.")
            session.save()

            # Dynamic profile sync
            composite = int((session.technical_score + session.communication_score) / 2)
            trainee.placement_readiness_score = int((trainee.placement_readiness_score + composite) / 2)
            trainee.save()

            messages.success(request, "Evaluation compiled! Check your scores.")
        else:
            # Generate next question
            session.current_question_index = round_count + 1
            session.save()

            dialogue_str = ""
            for m in session.messages.all():
                role_label = "Student" if m.role == 'trainee' else "Host Interviewer"
                dialogue_str += f"{role_label}: {m.content}\n\n"

            job_desc = session.job.description if session.job else "Standard position roleplay"
            skills_req = session.job.skills_required if session.job else trainee.skills

            next_quest = GeminiService.get_next_question(
                role_title=session.role_title,
                job_desc=job_desc,
                skills_list=skills_req,
                dialog_history_str=dialogue_str
            )

            InterviewMessage.objects.create(
                session=session,
                role='ai',
                content=next_quest
            )

        return redirect('ai:interview_session', session_id=session.id)

    # Format dialogue list for UI layout
    conversation_turns = []
    current_turn = {}
    for m in all_messages:
        if m.role == 'ai':
            if current_turn:
                conversation_turns.append(current_turn)
            current_turn = {'ai': m.content, 'trainee': None}
        elif m.role == 'trainee':
            if current_turn:
                current_turn['trainee'] = m.content
                conversation_turns.append(current_turn)
                current_turn = {}
    if current_turn:
        conversation_turns.append(current_turn)

    context = {
        'session': session,
        'conversation_turns': conversation_turns,
        'last_msg': all_messages.last() if all_messages.exists() else None,
    }
    return render(request, 'ai/interview_session.html', context)


@student_required
def career_guidance(request):
    """
    Phase 4 Chat Interface for Career Guidance Assistant.
    """
    trainee = request.user.trainee_profile
    session, created = CareerGuidanceSession.objects.get_or_create(trainee=trainee)
    chat_messages = session.messages.all()

    # Pre-populate greeting message if session newly spun up
    if chat_messages.count() == 0:
        greeting = (
            f"Hello {request.user.get_full_name() or request.user.username}! "
            "I am your personal AI Placement Advisor. "
            "I have loaded your profile. Ask me anything about career fits, recommended upskilling paths, "
            "or how to optimize your placement parameters!"
        )
        CareerGuidanceMessage.objects.create(
            session=session,
            role='ai',
            content=greeting
        )
        chat_messages = session.messages.all()

    # Suggested queries list
    suggested_questions = [
        "What jobs fit my tech stack best?",
        "Which technical skills should I pick up first?",
        "How can I maximize my corporate placement eligibility index?",
    ]

    context = {
        'session': session,
        'chat_messages': chat_messages,
        'suggested_questions': suggested_questions,
    }
    return render(request, 'ai/guidance.html', context)


@student_required
@require_POST
def career_guidance_send(request):
    """
    Processes chat requests via the chatbot interface.
    """
    trainee = request.user.trainee_profile
    session = get_object_or_404(CareerGuidanceSession, trainee=trainee)
    query = request.POST.get('query', '').strip()
    
    if not query:
        return redirect('ai:career_guidance')

    # Save user query
    CareerGuidanceMessage.objects.create(
        session=session,
        role='user',
        content=query
    )

    # Format context dialogue history
    dialogue_str = ""
    for m in session.messages.all().order_by('created_at')[:10]: # bound history limit
        role_lbl = "Student" if m.role == 'user' else "Advisor"
        dialogue_str += f"{role_lbl}: {m.content}\n"

    # Make call
    counsel_reply = GeminiService.get_career_guidance(
        trainee_profile=trainee,
        query=query,
        chat_history_str=dialogue_str
    )

    # Save advisor response
    CareerGuidanceMessage.objects.create(
        session=session,
        role='ai',
        content=counsel_reply
    )

    return redirect('ai:career_guidance')


@admin_required
def prompt_list(request):
    """
    Phase 7 List of registered Prompt Templates.
    """
    templates = PromptTemplate.objects.all()
    
    # If empty, boot them
    if templates.count() == 0:
        for name in FALLBACK_PROMPTS.keys():
            GeminiService.get_prompt(name)
        templates = PromptTemplate.objects.all()

    context = {
        'templates': templates,
    }
    return render(request, 'ai/prompt_list.html', context)


@admin_required
def prompt_edit(request, prompt_id):
    """
    Phase 7 Editor View to alter active API Prompts on the fly.
    """
    prompt = get_object_or_404(PromptTemplate, id=prompt_id)

    if request.method == 'POST':
        prompt.system_instruction = request.POST.get('system_instruction', '').strip()
        prompt.user_template = request.POST.get('user_template', '').strip()
        prompt.version += 1
        prompt.is_active = 'is_active' in request.POST
        prompt.save()

        messages.success(request, f"Properties for '{prompt.name}' saved and upgraded to version {prompt.version}!")
        return redirect('ai:prompt_list')

    context = {
        'prompt': prompt,
    }
    return render(request, 'ai/prompt_edit.html', context)
