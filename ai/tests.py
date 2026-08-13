# django_backend/ai/tests.py
"""
AI Suite Phase 10 Testing Suite.
Verifies resume assessment databases models, mock dialogue session transitions, 
dynamic prompt template injection mechanisms, and role-based access controllers.
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
User = get_user_model()
from django.urls import reverse
from accounts.models import UserProfile, Role
from accounts.models import TraineeProfile
from jobs.models import Job
from recruiters.models import RecruiterProfile
from .models import PromptTemplate, ResumeAnalysis, ResumeRoadmap, InterviewSession, InterviewMessage
from .services import GeminiService


class AIEngineTestCase(TestCase):
    """
    Validation matrix assessing AI Integration services and database schemas connectivity.
    """

    def setUp(self):
        # Create trainee user and profile
        self.trainee_user = User.objects.create_user(
            email='carl@nexthire.org',
            password='SecurePassword2026!',
            role=Role.TRAINEE
        )
        self.trainee_profile = TraineeProfile.objects.create(
            user=self.trainee_user,
            usn='1NH22CS045',
            degree=TraineeProfile.DegreeChoices.BTECH,
            branch='Computer Science & Engineering',
            cgpa=8.50,
            skills=['Python', 'Django', 'SQL'],
            certifications=['AWS Cloud Practictioner'],
            internships=[{'role': 'Fullstack Intern', 'company': 'InnoTech', 'duration': '3 Months'}],
            placement_readiness_score=75
        )

        # Create recruiter user and profile
        self.recruiter_user = User.objects.create_user(
            email='rebecca@recruiters.com',
            password='RecruiterSecure2026!',
            role=Role.RECRUITER
        )
        self.recruiter_user.save()
        self.recruiter_user.profile.save()
        
        self.recruiter_profile = RecruiterProfile.objects.create(
            user=self.recruiter_user,
            company_name='NextHire Tech Solutions'
        )

        # Create job posting
        self.job = Job.objects.create(
            recruiter=self.recruiter_profile,
            title='Backend Cloud Engineer',
            description='Looking for a junior engineer focused on Python REST APIs, security compliance, and MySQL scaling.',
            job_type=Job.JobType.FULL_TIME,
            location='Bengaluru, IND',
            salary_package='14 LPA',
            skills_required=['Python', 'Django', 'MySQL', 'Docker'],
            min_cgpa_required=7.00,
            application_deadline='2026-09-30'
        )

        self.client = Client()

    def test_prompt_template_bootstrap(self):
        """
        Verify prompts fallback and dynamic database bootstrapping.
        """
        prompt = GeminiService.get_prompt('resume_analysis')
        self.assertIsNotNone(prompt)
        self.assertIn("resume_score", prompt['system'])
        
        # Check that PromptTemplate record was generated in DB
        db_prompt = PromptTemplate.objects.filter(name='resume_analysis').first()
        self.assertIsNotNone(db_prompt)
        self.assertEqual(db_prompt.version, 1)

    def test_resume_parser_integration(self):
        """
        Validate Resume Intelligence analyses storage.
        """
        analysis = ResumeAnalysis.objects.create(
            trainee=self.trainee_profile,
            resume_score=85,
            resume_summary='Strong software development candidate.',
            missing_skills=['Docker', 'Kubernetes'],
            improvement_tips=['Add quantitative outcomes to project descriptions.']
        )
        self.assertEqual(analysis.resume_score, 85)
        self.assertEqual(analysis.trainee.usn, '1NH22CS045')
        self.assertIn('Docker', analysis.missing_skills)

    def test_mock_interview_flow(self):
        """
        Assess mock interview session setup, answer iteration cycles, and evaluation structures.
        """
        session = InterviewSession.objects.create(
            trainee=self.trainee_profile,
            job=self.job,
            role_title=self.job.title,
            current_question_index=1
        )
        
        # AI Question Message
        msg_ai = InterviewMessage.objects.create(
            session=session,
            role='ai',
            content='Can you explain the difference between processes and threads?'
        )
        
        # Student Answer Message
        msg_stud = InterviewMessage.objects.create(
            session=session,
            role='trainee',
            content='Processes obtain isolated memory models. Threads reside inside a process and share common address environments.'
        )

        self.assertEqual(session.current_question_index, 1)
        self.assertEqual(session.messages.count(), 2)
        self.assertEqual(msg_ai.role, 'ai')
        self.assertEqual(msg_stud.role, 'trainee')

    def test_resume_roadmap_blueprint_tracking(self):
        """
        Confirm Resume Improvement Roadmap structures update.
        """
        roadmap = ResumeRoadmap.objects.create(
            trainee=self.trainee_profile,
            weak_areas=['Microservices docker pipelines'],
            recommendations=['Earn Docker Certified Associate'],
            target_resume_suggestions='Add specific DevOps project details.',
            progress_percentage=20
        )
        self.assertEqual(roadmap.progress_percentage, 20)
        roadmap.progress_percentage += 30
        roadmap.save()
        self.assertEqual(roadmap.progress_percentage, 50)
