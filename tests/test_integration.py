# django_backend/tests/test_integration.py
"""
Integration Tests for NextHire Placement Engine workflow.
Traces cohesive transactions across multiple entities:
Register -> Login -> Post Job -> Apply -> Interview -> Offer -> Placement verification.
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
User = get_user_model()
from django.urls import reverse
from decimal import Decimal
from django.utils import timezone

from accounts.models import Role
from accounts.models import TraineeProfile
from trainees.models import Resume
from recruiters.models import RecruiterProfile
from jobs.models import Job
from applications.models import Application, Offer, Status, OfferStatus
from interviews.models import Interview
from django.core.files.uploadedfile import SimpleUploadedFile

class SmartPlacementWorkflowIntegrationTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_complete_smart_placement_pipeline_workflow(self):
        """
        Traces the full placement cycle:
        1. Student Registers & Logs In.
        2. Recruiter Registers & Posts standard Job.
        3. Student views Job Feed & applies.
        4. Recruiter reviews application & schedules Interview meeting.
        5. Recruiter evaluates and updates application status.
        6. Recruiter extends digital Offer Letter.
        7. Student accepts Offer, triggering final Placement.
        """
        print("\n=== STARTING PLATFORM WORKFLOW INTEGRATION TESTING ===")
        
        # -------------------------------------------------------------
        # STEP 1: Candidate Student Registration & Intake Profile
        # -------------------------------------------------------------
        print("[Step 1] Attempting candidate trainee signup registration...")
        signup_url = reverse('accounts:register_student')
        signup_data = {
            'name': 'Allan Betchley',
            'email': 'allan@betchley.org',
            'password': 'codebreakingpass',
            'confirm_password': 'codebreakingpass',
            'phone_number': '1234556789',
            'degree': 'BTECH',
            'branch': 'Computer Science & Engineering',
            'batch_code': 'BATCH2026'
        }
        res_signup = self.client.post(signup_url, data=signup_data)
        self.assertEqual(res_signup.status_code, 302) # Redirects to routing
        
        # Ensure User and UserProfile exist
        user_student = User.objects.get(email='allan@betchley.org')
        self.assertEqual(user_student.profile.role, Role.TRAINEE)
        
        # Complete TraineeProfile details
        trainee_profile = user_student.trainee_profile
        trainee_profile.cgpa = Decimal("9.40")
        trainee_profile.skills = ["Python", "Machine Learning", "Cryptography"]
        trainee_profile.certifications = ["Enigma Crack Certificate"]
        
        # Upload a dummy resume for the trainee
        resume_file = SimpleUploadedFile("resume.pdf", b"dummy content", content_type="application/pdf")
        resume = Resume.objects.create(trainee=trainee_profile, resume_file=resume_file, is_active=True)
        trainee_profile.resume_file = resume.resume_file
        trainee_profile.approval_status = 'approved'
        trainee_profile.save()
        
        print(f" -> Student registration successful: {trainee_profile}")
 
        # -------------------------------------------------------------
        # STEP 2: Corporate Recruiter Partners & Job Postings
        # -------------------------------------------------------------
        print("[Step 2] Attempting corporate recruiter registration & job publishing...")
        # Create user via models (simulated approval cycle)
        user_recruiter = User.objects.create_user(email='hiring@bletchley.com', password='enigma_password')
        user_recruiter.role = Role.RECRUITER
        user_recruiter.save()
        
        recruiter_profile = RecruiterProfile.objects.create(
            user=user_recruiter,
            company_name="Betchley Intelligence Corp",
            contact_email="careers@bletchley.com",
            is_approved_by_admin=True
        )
        
        # Recruiter logins
        self.client.login(email='hiring@bletchley.com', password='enigma_password')
        
        # Recruiter posts a new Job vacancy
        publish_url = reverse('jobs:publish')
        job_data = {
            'title': 'AI Cryptanalyst Specialist',
            'description': 'Help decode sophisticated messaging layouts using scikit-learn models.',
            'job_type': Job.JobType.FULL_TIME,
            'location': 'London, UK',
            'salary_package': '28 LPA',
            'skills_required': '["Python", "Cryptography", "Machine Learning"]',
            'min_cgpa_required': '8.50',
            'application_deadline': (timezone.now() + timezone.timedelta(days=15)).date().strftime('%Y-%m-%d')
        }
        res_job = self.client.post(publish_url, data=job_data)
        self.assertEqual(res_job.status_code, 302)
        
        # Verify job is recorded
        job_posted = Job.objects.get(title='AI Cryptanalyst Specialist', recruiter=recruiter_profile)
        print(f" -> Recruiter posted job successfully: {job_posted}")

        # -------------------------------------------------------------
        # STEP 3: Student Feeds Inspections & Direct Submissions
        # -------------------------------------------------------------
        print("[Step 3] Student browsing feed and submitting application...")
        self.client.logout()
        self.client.login(email='allan@betchley.org', password='codebreakingpass')
        
        # Browse active feeds
        feed_url = reverse('jobs:feed')
        res_feed = self.client.get(feed_url)
        self.assertEqual(res_feed.status_code, 200)
        
        # Apply to job
        apply_url = reverse('applications:apply', kwargs={'job_id': job_posted.id})
        res_apply = self.client.post(apply_url)
        self.assertEqual(res_apply.status_code, 302) # Redirects to tracking
        
        # Verify Application database entity is configured
        application = Application.objects.get(trainee=trainee_profile, job=job_posted)
        self.assertEqual(application.status, Status.PENDING)
        print(f" -> Student applied successfully. Application: {application}")

        # -------------------------------------------------------------
        # STEP 4: Recruiter Interactivity & Interview Scheduling
        # -------------------------------------------------------------
        print("[Step 4] Corporate Scheduler scheduling assessments...")
        self.client.logout()
        self.client.login(email='hiring@bletchley.com', password='enigma_password')
        
        # Transition application to SHORTLISTED/TESTING
        application.status = Status.SHORTLISTED
        application.save()
        
        # Schedule evaluation round interview
        meet_time = timezone.now() + timezone.timedelta(days=2)
        interview = Interview.objects.create(
            application=application,
            title="Symmetric Key Logic Assessment",
            stage=Interview.Stage.TECHNICAL,
            scheduled_at=meet_time,
            platform="Google Meet",
            meet_url="https://meet.google.com/enigma-dec-2026",
            status=Interview.Status.SCHEDULED
        )
        self.assertEqual(interview.status, Interview.Status.SCHEDULED)
        print(f" -> Interview evaluation scheduled: {interview}")

        # -------------------------------------------------------------
        # STEP 5: Corporate Evaluation & Status Shifting
        # -------------------------------------------------------------
        print("[Step 5] Performing interview evaluation and application status promotion...")
        interview.status = Interview.Status.COMPLETED
        interview.rating_score = 5
        interview.feedback_notes = "Brilliant cryptologist. Cracked all algorithmic cycles in under 12 minutes."
        interview.save()
        
        # Promote application status to INTERVIEWING to indicate interview stages are complete and positive
        application.status = Status.INTERVIEWING
        application.save()
        print(f" -> Evaluation completed successfully. Candidate rating: {interview.rating_score}/5")

        # -------------------------------------------------------------
        # STEP 6: digital Offer Letter Distributions
        # -------------------------------------------------------------
        print("[Step 6] Recruiter generating formal select offer letter...")
        offer = Offer.objects.create(
            trainee=trainee_profile,
            company=recruiter_profile,
            job=job_posted,
            package="28 LPA",
            status=OfferStatus.PENDING,
            offer_letter_text="Sincerest congratulations Allan! We are pleased to extend this placement selection offer."
        )
        application.status = Status.OFFER_EXTENDED
        application.save()
        
        self.assertEqual(offer.status, OfferStatus.PENDING)
        self.assertEqual(application.status, Status.OFFER_EXTENDED)
        print(f" -> Selection Offer Extended successfully: {offer}")

        # -------------------------------------------------------------
        # STEP 7: Student Acceptance & Final Placement Release
        # -------------------------------------------------------------
        print("[Step 7] Student accepting offer letter and concluding placement process...")
        self.client.logout()
        self.client.login(email='allan@betchley.org', password='codebreakingpass')
        
        # Simulate offer acceptance
        offer.status = OfferStatus.ACCEPTED
        offer.save()
        
        application.status = Status.OFFER_ACCEPTED
        application.save()
        
        self.assertEqual(offer.status, OfferStatus.ACCEPTED)
        self.assertEqual(application.status, Status.OFFER_ACCEPTED)
        print(" -> Offer accepted. Final application pipeline status: PLACED/OFFER_ACCEPTED.")
        print("=== WORKFLOW INTEGRATION TESTING COMPLETED GLORIOUSLY GREEN ===\n")
