# django_backend/tests/test_models.py
"""
Unit tests for NextHire's Model layer.
Asserts model structures, automatic signal triggers, property methods,
and database validation bounds across all core sub-apps.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
User = get_user_model()
from decimal import Decimal
from django.utils import timezone

from accounts.models import UserProfile, Role
from accounts.models import TraineeProfile
from recruiters.models import RecruiterProfile
from jobs.models import Job
from applications.models import Application, Offer, Status, OfferStatus
from interviews.models import Interview
from notifications.models import Notification
from ml_engine.models import MLModelMetadata, CandidatePlacementPrediction, JobRecommendationCache

class AccountsModelTests(TestCase):
    def test_automatic_profile_creation_on_user_save(self):
        """Verify that creating a User triggers saving a UserProfile with appropriate default role."""
        # Clear existing seeded users so user1 is the first user
        User.objects.all().delete()
        
        # The first user created should default to ADMIN
        user1 = User.objects.create_user(email='admin@nexthire.net', password='adminpassword')
        self.assertEqual(user1.profile.role, Role.ADMIN)
        
        # Subsequent users should default to STUDENT
        user2 = User.objects.create_user(email='cand@nexthire.net', password='candpassword')
        self.assertEqual(user2.profile.role, Role.TRAINEE)
        self.assertFalse(user2.profile.is_verified)
        
        # Test string presentation
        self.assertEqual(str(user2.profile), f"{user2.email} (trainee)")


class StudentsModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='student@nexthire.net', password='password123', role=Role.TRAINEE)
        
    def test_student_profile_completion_percentage(self):
        """Assert profile_completion_percentage property computes metric correctly based on filled fields."""
        trainee_profile = TraineeProfile.objects.create(
            user=self.user,
            usn="1RV22MC001",
            degree=TraineeProfile.DegreeChoices.MCA,
            branch="Computer Applications",
            cgpa=Decimal("8.50"),
            skills=["Python", "Django"],
            certifications=[],
            internships=[]
        )
        # Expected filled factors from attributes list:
        # User first_name (empty), user last_name (empty), user email (filled),
        # phone_number (empty), address (empty), profile_image (empty),
        # degree (filled), branch (filled), cgpa (filled), skills (filled),
        # certifications (empty), internships (empty), resume_file (empty)
        # Total list length: 13. Filled attributes: email, degree, branch, cgpa, skills = 5 filled.
        # Completion percentage is int((5 / 13) * 100) = 38%
        percentage = trainee_profile.profile_completion_percentage
        self.assertEqual(percentage, 38)
        
        # Fill in first_name, last_name, phone_number, and certifications
        self.user.first_name = "Jane"
        self.user.last_name = "Doe"
        self.user.save()
        trainee_profile.phone_number = "+919876543210"
        trainee_profile.certifications = ["AWS Practitioner"]
        trainee_profile.save()
        
        # We filled 4 more values. Total filled: 9 / 13 = 69%
        self.assertEqual(trainee_profile.profile_completion_percentage, 69)

    def test_student_profile_string_representation(self):
        trainee_profile = TraineeProfile.objects.create(
            user=self.user,
            usn="1RV22MC001",
            cgpa=Decimal("9.00")
        )
        self.assertEqual(str(trainee_profile), f"{self.user.email} (1RV22MC001)")


class RecruitersModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='recruiter@nexthire.net', password='password123', role=Role.RECRUITER)

    def test_recruiter_profile_creation(self):
        profile = RecruiterProfile.objects.create(
            user=self.user,
            company_name="Aperture Science Inc",
            industry_domain="SaaS / Robotics",
            company_website="https://aperture.science",
            contact_email="careers@aperture.science"
        )
        self.assertFalse(profile.is_approved_by_admin)
        self.assertEqual(str(profile), "Aperture Science Inc - recruiter@nexthire.net")


class JobsModelTests(TestCase):
    def setUp(self):
        self.recruiter_user = User.objects.create_user(email='rec@aperture.com', password='rec_password', role=Role.RECRUITER)
        self.recruiter_profile = RecruiterProfile.objects.create(
            user=self.recruiter_user,
            company_name="Aperture Labs",
            contact_email="hiring@aperture.com"
        )

    def test_job_posting_creation(self):
        job = Job.objects.create(
            recruiter=self.recruiter_profile,
            title="SRE Engineer",
            description="Looking for SRE specialists with Python and Linux knowledge.",
            job_type=Job.JobType.FULL_TIME,
            location="Bengaluru, IND",
            salary_package="14 LPA",
            skills_required=["Python", "Linux", "Docker"],
            min_cgpa_required=Decimal("7.50"),
            application_deadline=timezone.now().date() + timezone.timedelta(days=15)
        )
        self.assertTrue(job.is_active)
        self.assertEqual(str(job), "SRE Engineer @ Aperture Labs")


class ApplicationsAndOffersModelTests(TestCase):
    def setUp(self):
        # Setup student
        self.stud_user = User.objects.create_user(email='john@nexthire.net', password='pwd', role=Role.TRAINEE)
        self.trainee = TraineeProfile.objects.create(
            user=self.stud_user,
            usn="1RV22BATCH",
            cgpa=Decimal("8.20")
        )
        # Setup job
        self.rec_user = User.objects.create_user(email='rec_user_comp@nexthire.net', password='pwd', role=Role.RECRUITER)
        self.recruiter = RecruiterProfile.objects.create(user=self.rec_user, company_name="Globex Corp", contact_email="comp@globex.com")
        self.job = Job.objects.create(
            recruiter=self.recruiter,
            title="Backend Architect",
            description="Django Architect",
            skills_required=["Django"],
            min_cgpa_required=Decimal("6.50"),
            application_deadline=timezone.now().date() + timezone.timedelta(days=30)
        )

    def test_job_application_lifecycle(self):
        # Create application
        app = Application.objects.create(
            trainee=self.trainee,
            job=self.job,
            status=Status.PENDING,
            screener_score=85
        )
        self.assertEqual(app.status, Status.PENDING)
        self.assertEqual(str(app), f"{self.stud_user.email} -> {self.job.title} ({Status.PENDING})")

        # Create offer letter
        offer = Offer.objects.create(
            trainee=self.trainee,
            company=self.recruiter,
            job=self.job,
            package="18 LPA",
            status=OfferStatus.PENDING
        )
        self.assertEqual(offer.status, OfferStatus.PENDING)
        self.assertIn("We are pleased to extend", offer.offer_letter_text)
        self.assertEqual(str(offer), f"Offer from Globex Corp to {self.stud_user.email} for {self.job.title} (PENDING)")


class InterviewsModelTests(TestCase):
    def setUp(self):
        self.stud_user = User.objects.create_user(email='stud_interviews@nexthire.net', password='pwd', role=Role.TRAINEE)
        self.trainee = TraineeProfile.objects.create(user=self.stud_user, usn="1RVTEST", cgpa=Decimal("8.00"))
        self.rec_user = User.objects.create_user(email='rec_interviews@nexthire.net', password='pwd', role=Role.RECRUITER)
        self.recruiter = RecruiterProfile.objects.create(user=self.rec_user, company_name="Initech", contact_email="hiring@initech.net")
        self.job = Job.objects.create(
            recruiter=self.recruiter,
            title="QA Automation Engineer",
            skills_required=["Python"],
            application_deadline=timezone.now().date() + timezone.timedelta(days=10)
        )
        self.app = Application.objects.create(trainee=self.trainee, job=self.job, status=Status.SHORTLISTED)

    def test_interview_scheduling_creation(self):
        sched_time = timezone.now() + timezone.timedelta(days=3)
        interview = Interview.objects.create(
            application=self.app,
            title="Technical Discussion Round 1",
            stage=Interview.Stage.TECHNICAL,
            scheduled_at=sched_time,
            platform="Google Meet",
            meet_url="https://meet.google.com/abc-defg-hij",
            status=Interview.Status.SCHEDULED
        )
        self.assertEqual(interview.stage, Interview.Stage.TECHNICAL)
        self.assertEqual(interview.status, Interview.Status.SCHEDULED)
        self.assertEqual(interview.meet_url, "https://meet.google.com/abc-defg-hij")


class NotificationsModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='notify@nexthire.net', password='pwd', role=Role.TRAINEE)

    def test_notification_dispatch_stub_success(self):
        notify = Notification.objects.create(
            user=self.user,
            title="New Application Match",
            message="Your profile has matched with Aperture Automation.",
            notification_type=Notification.Type.STATUS_UPDATE
        )
        self.assertFalse(notify.is_read)
        self.assertEqual(str(notify), f"{self.user.email} | New Application Match (Unread)")
        # Test dispatch_email runs cleanly
        success = notify.dispatch_email()
        # By default in testing settings, django.core.mail.send_mail outputs locally using LocMemBackend or fallback
        self.assertTrue(success)


class MachineLearningModelTests(TestCase):
    def test_ml_metadata_preservation(self):
        meta = MLModelMetadata.objects.create(
            version="v2026.06.11",
            algorithm_name="RandomForestClassifier",
            accuracy=0.885,
            precision=0.87,
            recall=0.89,
            f1_score=0.88,
            model_file_path="/safe/path/to/placement_clf_v2026.06.11.joblib",
            features_used=["cgpa", "skills_count", "internship", "certifications", "aptitude_score", "projects"],
            is_active=True,
            description="Production-grade placement predictor v1."
        )
        self.assertEqual(meta.accuracy_percentage, 88.5)
        self.assertTrue(meta.is_active)
        self.assertIn("ACTIVE", str(meta))
