# trainees/tests.py
"""
Django test cases for NextHire Student Module.
Validates candidate registrations, authentication, dashboard data aggregates, 
resume validations, and profile modifications.
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
User = get_user_model()
from django.core.files.uploadedfile import SimpleUploadedFile
from accounts.models import UserProfile, Role
from accounts.models import TraineeProfile
from jobs.models import Job
from recruiters.models import RecruiterProfile
from applications.models import Application, Status
import json

class StudentModuleTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        
        # 1. Generate auth core trainee user
        self.trainee_user = User.objects.create_user(
            email='sam@college.edu', 
            password='SecurePassword123'
        )
        self.trainee_user.first_name = 'Sam'
        self.trainee_user.last_name = 'Student'
        self.trainee_user.save()
        
        # Trigger signal setup verification:
        # Accounts post_save signal should instantly provision user profiles Choice Choice.Role
        self.profile = self.trainee_user.profile
        self.profile.role = Role.TRAINEE
        self.profile.save()
        
        # 2. Complete trainee profile details
        self.trainee_profile = TraineeProfile.objects.create(
            user=self.trainee_user,
            usn='USN202611A',
            degree=TraineeProfile.DegreeChoices.MCA,
            branch='Computer Applications',
            cgpa=8.50,
            skills=['Python', 'Django'],
            placement_readiness_score=80
        )

        # 3. Create a Recruiting partner and an active Job Listing for matching recommendations
        self.recruiter_user = User.objects.create_user(
            email='jobs@employer.com', 
            password='CompanyPassword123'
        )
        self.recruiter_profile = RecruiterProfile.objects.create(
            user=self.recruiter_user,
            company_name='Apex Software Corp',
            industry_domain='Enterprise Saas',
            contact_email='jobs@apexsaas.com',
            is_approved_by_admin=True
        )
        self.rec_profile = self.recruiter_user.profile
        self.rec_profile.role = Role.RECRUITER
        self.rec_profile.save()

        self.eligible_job = Job.objects.create(
            recruiter=self.recruiter_profile,
            title='Backend Eng (Python)',
            description='Enjoys coding standard Django controllers.',
            salary_package='14 LPA',
            skills_required=['Python', 'Django'],
            min_cgpa_required=7.50,
            is_active=True,
            application_deadline='2026-12-31'
        )

        self.ineligible_job = Job.objects.create(
            recruiter=self.recruiter_profile,
            title='Quantum Architect specialist',
            description='Highly math specialized requirements.',
            salary_package='25 LPA',
            skills_required=['Qiskit', 'Astrophysics'],
            min_cgpa_required=9.50,
            is_active=True,
            application_deadline='2026-12-31'
        )

    def test_student_profile_signal_generation(self):
        """
        Verify that creating a user automatically triggers signal handlers 
        provisioning a matching UserProfile with correct standard roles mapping.
        """
        new_user = User.objects.create_user(email='new_guy@college.edu', password='Pw')
        self.assertTrue(UserProfile.objects.filter(id=new_user.id).exists())
        self.assertEqual(new_user.profile.role, Role.TRAINEE)

    def test_student_dashboard_authorization_gating(self):
        """
        Phase 7 - Ensure trainee-specific views reject unauthorized users
        and redirect them to safety.
        """
        # Unauthenticated request should redirect
        response = self.client.get(reverse('trainees:dashboard'))
        self.assertEqual(response.status_style if hasattr(response, 'status_style') else response.status_code, 302)
        self.assertIn('/accounts/login', response.url)

    def test_student_dashboard_compilation(self):
        """
        Phase 2 & 5 - Verify trainee dashboard loads successful aggregates,
        eligibility-matched recommendations, and notifies arrays.
        """
        self.client.login(email='sam@college.edu', password='SecurePassword123')
        response = self.client.get(reverse('trainees:dashboard'))
        self.assertEqual(response.status_code, 200)
        
        # Verify Context Variables are correct
        self.assertEqual(response.context['trainee'].usn, 'USN202611A')
        self.assertEqual(response.context['applied_count'], 0)
        self.assertEqual(response.context['readiness_score'], 80)
        
        # Sam should be recommended the Python role, but not the Quantum Role
        recommended_roles = response.context['recommended_jobs']
        self.assertIn(self.eligible_job, recommended_roles)
        self.assertNotIn(self.ineligible_job, recommended_roles)

    def test_student_profile_update(self):
        """
        Phase 3 - Submit personal profile details updates. Ensure parsing comma
        separated values maps correctly back to JSON array blocks in DB models.
        """
        self.client.login(email='sam@college.edu', password='SecurePassword123')
        
        # Update details
        post_data = {
            'first_name': 'Samuel',
            'last_name': 'Student',
            'email': 'samuel_student@gmail.com',
            'phone_number': '+91 99008811A2',
            'address': '12 Forest Green Ave, Bangalore Karnataka',
            'degree': TraineeProfile.DegreeChoices.BTECH,
            'branch': 'Information Science Dept',
            'cgpa': '8.80',
            'raw_skills': 'Python, Celery, Redis, Kubernetes',
            'raw_certifications': 'AWS Cloud Pro',
            'raw_internships': 'Backend Intern @ TechShop'
        }
        
        response = self.client.post(reverse('trainees:profile'), data=post_data)
        # Success redirects to dashboard
        self.assertEqual(response.status_code, 302)
        
        # Verify modifications inside DB
        self.trainee_profile.refresh_from_db()
        self.trainee_user.refresh_from_db()
        self.assertEqual(self.trainee_user.first_name, 'Samuel')
        self.assertEqual(float(self.trainee_profile.cgpa), 8.80)
        self.assertEqual(self.trainee_profile.skills, ['Python', 'Celery', 'Redis', 'Kubernetes'])
        self.assertEqual(self.trainee_profile.certifications, ['AWS Cloud Pro'])
        self.assertEqual(self.trainee_profile.internships, ['Backend Intern @ TechShop'])

    def test_resume_upload_and_format_validation(self):
        """
        Phase 4 - Tests file formats validations (PDF & DOCX acceptable).
        Blocks malicious non-compliant formats.
        """
        self.client.login(email='sam@college.edu', password='SecurePassword123')
        
        # 1. Attempt uploading invalid format (.exe payload)
        bad_file = SimpleUploadedFile("payload.exe", b"binarycontent", content_type="application/octet-stream")
        response = self.client.post(reverse('trainees:resume'), {
            'resume_file': bad_file
        })
        # Validation error should trigger re-render of forms page with failed messages
        self.assertEqual(response.status_code, 200)
        self.trainee_profile.refresh_from_db()
        self.assertIsNone(self.trainee_profile.resume_file.name or None)

        # 2. UpLoading conforming PDF format
        good_file = SimpleUploadedFile("portfolio_resume.pdf", b"pdfcontent_bytestream", content_type="application/pdf")
        response = self.client.post(reverse('trainees:resume'), {
            'resume_file': good_file
        }, follow=True)
        # Should redirect to details page
        self.assertEqual(response.status_code, 200)
        
        self.trainee_profile.refresh_from_db()
        self.assertIsNotNone(self.trainee_profile.resume_file)
        self.assertTrue(self.trainee_profile.resume_file.name.endswith('.pdf'))
        
        # Check that Resume model instance is created
        from trainees.models import Resume
        self.assertTrue(Resume.objects.filter(trainee=self.trainee_profile).exists())
        self.assertEqual(Resume.objects.filter(trainee=self.trainee_profile).count(), 1)

    def test_resume_deletion(self):
        """Verify that deleting a resume removes the database record and the file."""
        self.client.login(email='sam@college.edu', password='SecurePassword123')
        
        # Upload first
        good_file = SimpleUploadedFile("portfolio_resume.pdf", b"pdfcontent_bytestream", content_type="application/pdf")
        self.client.post(reverse('trainees:resume'), {
            'resume_file': good_file
        })
        
        # Deletion
        response = self.client.post(reverse('trainees:resume_delete'))
        self.assertEqual(response.status_code, 302) # Redirect to resume page
        
        self.trainee_profile.refresh_from_db()
        self.assertIsNone(self.trainee_profile.resume_file.name or None)
        
        # Verify Resume model record is deleted
        from trainees.models import Resume
        self.assertFalse(Resume.objects.filter(trainee=self.trainee_profile).exists())
