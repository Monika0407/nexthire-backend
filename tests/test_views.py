# django_backend/tests/test_views.py
"""
Unit tests for NextHire's View and Controller layer.
Asserts authentication gateways, dashboard permissions, forms submission processing,
and security restrictions on role access.
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
User = get_user_model()
from django.urls import reverse
from decimal import Decimal
from django.utils import timezone

from accounts.models import UserProfile, Role
from accounts.models import TraineeProfile
from recruiters.models import RecruiterProfile
from jobs.models import Job
from applications.models import Application, Status

class AuthAndRedirectionViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Student credentials
        self.stud_user = User.objects.create_user(email='johnny@trainee.com', password='secretpassword', role=Role.TRAINEE)
        
        # Recruiter credentials
        self.rec_user = User.objects.create_user(email='tony@stark.com', password='starkpassword', role=Role.RECRUITER)
        self.rec_profile = self.rec_user.profile
        self.rec_profile.role = Role.RECRUITER
        self.rec_profile.save()

    def test_anonymous_user_dashboard_redirects_to_login(self):
        """Verify redirect to login when accessing authenticated-only pages as an anonymous user."""
        response = self.client.get(reverse('accounts:role_routing'))
        self.assertEqual(response.status_code, 302)
        # Should redirect to login url
        self.assertIn('/accounts/login/', response.url)

    def test_role_based_routing_gateway(self):
        """Verify the routing gateway directs users to the appropriate dashboard depending on theirs roles."""
        # 1. Login as Student
        logged_in = self.client.login(email='johnny@trainee.com', password='secretpassword')
        self.assertTrue(logged_in)
        
        # Student profile needs to exist and be approved
        TraineeProfile.objects.create(user=self.stud_user, usn="1RV22B102", cgpa=Decimal("8.10"), approval_status='approved')
        
        response = self.client.get(reverse('accounts:role_routing'))
        self.assertEqual(response.status_code, 302)
        # Redirect to Student Dashboard
        self.assertEqual(response.url, reverse('trainees:dashboard'))
        self.client.logout()

        # 2. Login as Recruiter
        logged_in_rec = self.client.login(email='tony@stark.com', password='starkpassword')
        self.assertTrue(logged_in_rec)
        
        # Recruiter profile needs to exist and be approved
        RecruiterProfile.objects.create(user=self.rec_user, company_name="Stark Corp", contact_email="tony@stark.com", is_approved_by_admin=True)
        
        response = self.client.get(reverse('accounts:role_routing'))
        self.assertEqual(response.status_code, 302)
        # Redirect to Recruiter Dashboard
        self.assertEqual(response.url, reverse('recruiters:dashboard'))


class JobsAndApplicationsViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Setup corporate partner
        self.rec_user = User.objects.create_user(email='recruiter@waynecorp.com', password='hr_password', role=Role.RECRUITER)
        self.rec_profile = self.rec_user.profile
        self.rec_profile.role = Role.RECRUITER
        self.rec_profile.save()
        self.rec_comp_profile = RecruiterProfile.objects.create(
            user=self.rec_user,
            company_name="Wayne Enterprises",
            contact_email="hiring@waynecorp.com",
            is_approved_by_admin=True
        )

        # Setup standard trainee
        self.stud_user = User.objects.create_user(email='peter@trainee.com', password='stud_password', role=Role.TRAINEE)
        self.trainee_profile = TraineeProfile.objects.create(
            user=self.stud_user,
            usn="1RV22MC999",
            cgpa=Decimal("8.80"),
            skills=["Python", "Go"],
            approval_status="approved"
        )

        # Post an active job
        self.job = Job.objects.create(
            recruiter=self.rec_comp_profile,
            title="Senior Systems Engineer",
            description="Manage scalable systems",
            skills_required=["Go", "Linux"],
            min_cgpa_required=Decimal("7.00"),
            application_deadline=timezone.now().date() + timezone.timedelta(days=10)
        )

    def test_student_can_apply_to_job(self):
        """Verify standard trainees can apply to active postings and that database rows are configured."""
        self.client.login(email='peter@trainee.com', password='stud_password')
        
        apply_url = reverse('applications:apply', kwargs={'job_id': self.job.id})
        response = self.client.post(apply_url)
        
        # Redirect dynamically on success to application tracking
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('applications:tracking'))
        
        # Verify row creation
        app_exists = Application.objects.filter(trainee=self.trainee_profile, job=self.job).exists()
        self.assertTrue(app_exists)
        app_obj = Application.objects.get(trainee=self.trainee_profile, job=self.job)
        self.assertEqual(app_obj.status, Status.PENDING)

    def test_recruiter_can_post_job(self):
        """Verify corporate partners can submit forms and publish job posts."""
        self.client.login(email='recruiter@waynecorp.com', password='hr_password')
        
        publish_url = reverse('jobs:publish')
        form_data = {
            'title': 'Frontend Engineer (React)',
            'description': 'Develop beautiful web interfaces.',
            'job_type': 'FULL_TIME',
            'location': 'Mumbai, IND',
            'salary_package': '12 LPA',
            'skills_required': '["React", "CSS"]',
            'min_cgpa_required': '6.50',
            'application_deadline': (timezone.now() + timezone.timedelta(days=20)).date().strftime('%Y-%m-%d')
        }
        response = self.client.post(publish_url, data=form_data)
        
        # Should redirect on success
        self.assertEqual(response.status_code, 302)
        
        # Verify job is successfully created in database
        self.assertTrue(Job.objects.filter(title='Frontend Engineer (React)', recruiter=self.rec_comp_profile).exists())


class StudentCourseDetailsViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.stud_user = User.objects.create_user(email='course_student@nexthire.com', password='password123', role=Role.TRAINEE)
        self.trainee_profile = TraineeProfile.objects.create(
            user=self.stud_user,
            usn="1RV22B333",
            cgpa=Decimal("8.50"),
            batch_code="ORIG_BATCH",
            approval_status="approved"
        )
        self.admin_user = User.objects.create_superuser(email='admin@nexthire.com', password='adminpassword')

    def test_course_details_view_accessible(self):
        """Verify trainee can access their course details view."""
        self.client.login(email='course_student@nexthire.com', password='password123')
        response = self.client.get(reverse('trainees:course_details'))
        self.assertEqual(response.status_code, 200)

    def test_request_edit_flow(self):
        """Verify request edit flow works and admin/trainer can approve/reject it."""
        # Student submits updated batch code directly
        self.client.login(email='course_student@nexthire.com', password='password123')
        update_url = reverse('trainees:course_details')
        response = self.client.post(update_url, {
            'batch_code': 'NEW_BATCH_CODE',
            'batch_timing': 'Morning',
            'current_status': 'Training'
        })
        self.assertEqual(response.status_code, 302)
        self.trainee_profile.refresh_from_db()
        self.assertEqual(self.trainee_profile.batch_code, 'NEW_BATCH_CODE')
        self.assertEqual(self.trainee_profile.approval_status, 'pending')
        self.assertEqual(self.trainee_profile.course_edit_request_status, 'pending')
        
        # Admin approves edit request
        self.client.login(email='admin@nexthire.com', password='adminpassword')
        approve_url = reverse('admin_custom:trainees')
        response = self.client.post(approve_url, {
            'trainee_id': self.trainee_profile.id,
            'action': 'approve_course_edit'
        })
        self.assertEqual(response.status_code, 302)
        self.trainee_profile.refresh_from_db()
        self.assertEqual(self.trainee_profile.approval_status, 'approved')
        self.assertEqual(self.trainee_profile.course_edit_request_status, 'approved')

