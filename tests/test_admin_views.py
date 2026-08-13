# django_backend/tests/test_admin_views.py
"""
Unit tests for NextHire's Custom Platform Administration views and control systems.
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
User = get_user_model()
from django.urls import reverse
from decimal import Decimal
from django.utils import timezone

from accounts.models import Role, TraineeProfile, RecruiterProfile, Course
from jobs.models import Job
from applications.models import Application, Status
from trainees.models import Resume

class AdminViewsTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Admin user credentials
        self.admin_user = User.objects.create_superuser(
            email='admin@nexthire.com',
            password='adminpassword'
        )

        # Create dummy course
        self.course, _ = Course.objects.get_or_create(name='Java Full Stack')

        # Standard trainee user credentials
        self.stud_user = User.objects.create_user(
            email='trainee@nexthire.com',
            password='studentpassword',
            role=Role.TRAINEE
        )
        self.stud_profile = TraineeProfile.objects.create(
            user=self.stud_user,
            usn='1RV22CS001',
            cgpa=Decimal('8.50'),
            skills=['Python', 'Django']
        )
        self.stud_profile.courses.add(self.course)

        # Recruiter user credentials
        self.rec_user = User.objects.create_user(
            email='recruiter@nexthire.com',
            password='recruiterpassword',
            role=Role.RECRUITER
        )
        self.rec_profile = RecruiterProfile.objects.create(
            user=self.rec_user,
            company_name='NextHire Tech Solutions',
            contact_email='hr@nexthire.com',
            is_approved_by_admin=False
        )

        # Create dummy job vacancy
        self.job = Job.objects.create(
            recruiter=self.rec_profile,
            title='Software Engineer intern',
            description='Django backend developer role',
            skills_required=['Python', 'Django'],
            min_cgpa_required=Decimal('7.00'),
            application_deadline=timezone.now().date() + timezone.timedelta(days=5),
            is_active=True
        )
        self.job.required_courses.add(self.course)

        # Create dummy application
        self.application = Application.objects.create(
            trainee=self.stud_profile,
            job=self.job,
            status=Status.PENDING
        )

    def test_non_admin_redirected(self):
        """Verify standard trainee users are prohibited from accessing admin endpoints."""
        self.client.login(email='trainee@nexthire.com', password='studentpassword')
        
        urls = [
            reverse('admin_custom:dashboard'),
            reverse('admin_custom:trainees'),
            reverse('admin_custom:recruiters'),
            reverse('admin_custom:jobs'),
            reverse('admin_custom:applications'),
        ]
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)

    def test_admin_dashboard_render_metrics(self):
        """Verify admin can load the dashboard panel which displays the core platform metrics."""
        self.client.login(email='admin@nexthire.com', password='adminpassword')
        
        response = self.client.get(reverse('admin_custom:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Admin Control Room")
        self.assertEqual(response.context['total_students'], 1)
        self.assertEqual(response.context['total_recruiters'], 1)
        self.assertEqual(response.context['total_jobs'], 1)
        self.assertEqual(response.context['total_applications'], 1)

    def test_admin_students_activation_toggle(self):
        """Verify admin can search for trainee records and toggle their activation status."""
        self.client.login(email='admin@nexthire.com', password='adminpassword')

        # 1. Access trainee listing page
        response = self.client.get(reverse('admin_custom:trainees'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'trainee@nexthire.com')

        # 2. Deactivate trainee
        self.assertTrue(self.stud_user.is_active)
        post_data = {
            'action': 'toggle_active',
            'user_id': self.stud_user.id
        }
        response = self.client.post(reverse('admin_custom:trainees'), data=post_data)
        self.assertEqual(response.status_code, 302)
        
        # Verify trainee is now deactivated
        self.stud_user.refresh_from_db()
        self.assertFalse(self.stud_user.is_active)

        # 3. Activate trainee back
        response = self.client.post(reverse('admin_custom:trainees'), data=post_data)
        self.assertEqual(response.status_code, 302)
        self.stud_user.refresh_from_db()
        self.assertTrue(self.stud_user.is_active)

    def test_admin_recruiters_verification_workflow(self):
        """Verify admin can verify and approve or disapprove recruiter registrations."""
        self.client.login(email='admin@nexthire.com', password='adminpassword')

        # 1. Access recruiters listing page
        response = self.client.get(reverse('admin_custom:recruiters'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'NextHire Tech Solutions')

        # 2. Approve recruiter
        self.assertFalse(self.rec_profile.is_approved_by_admin)
        post_data = {
            'recruiter_id': self.rec_profile.id,
            'action': 'approve'
        }
        response = self.client.post(reverse('admin_custom:recruiters'), data=post_data)
        self.assertEqual(response.status_code, 302)

        # Verify recruiter is approved
        self.rec_profile.refresh_from_db()
        self.assertTrue(self.rec_profile.is_approved_by_admin)

        # 3. Disapprove recruiter
        post_data['action'] = 'reject'
        response = self.client.post(reverse('admin_custom:recruiters'), data=post_data)
        self.assertEqual(response.status_code, 302)

        # Verify recruiter status is revoked
        self.rec_profile.refresh_from_db()
        self.assertFalse(self.rec_profile.is_approved_by_admin)

    def test_admin_jobs_filtering_and_modification(self):
        """Verify admin can list, filter, edit, and delete job postings."""
        self.client.login(email='admin@nexthire.com', password='adminpassword')

        # 1. Verify filtering
        response = self.client.get(reverse('admin_custom:jobs'), {'status': 'open'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['jobs']), 1)

        response = self.client.get(reverse('admin_custom:jobs'), {'status': 'closed'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['jobs']), 0)

        # 2. Save edit specs changes
        post_data = {
            'action': 'save_edit',
            'job_id': self.job.id,
            'title': 'Senior Software Architect',
            'description': 'Architect backend scaling pipelines.',
            'job_type': 'FULL_TIME',
            'location': 'Hyderabad, IND',
            'salary_package': '18 LPA',
            'min_cgpa_required': '7.50',
            'raw_skills': 'Python, Django, AWS, Kubernetes',
            'application_deadline': (timezone.now() + timezone.timedelta(days=10)).date().strftime('%Y-%m-%d'),
            'is_active': 'on',
            'required_courses': [self.course.id]
        }
        response = self.client.post(reverse('admin_custom:jobs'), data=post_data)
        self.assertEqual(response.status_code, 302)
        
        self.job.refresh_from_db()
        self.assertEqual(self.job.title, 'Senior Software Architect')
        self.assertEqual(self.job.salary_package, '18 LPA')
        self.assertEqual(self.job.skills_required, ['Python', 'Django', 'AWS', 'Kubernetes'])

        # 3. Delete job posting
        delete_data = {
            'action': 'delete',
            'job_id': self.job.id
        }
        response = self.client.post(reverse('admin_custom:jobs'), data=delete_data)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Job.objects.filter(id=self.job.id).exists())

    def test_admin_applications_status_tracking(self):
        """Verify admin can list and filter candidate applications."""
        self.client.login(email='admin@nexthire.com', password='adminpassword')

        response = self.client.get(reverse('admin_custom:applications'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'trainee@nexthire.com')
        self.assertEqual(len(response.context['applications']), 1)

        # Filter by status which has no entries (e.g. SHORTLISTED)
        response = self.client.get(reverse('admin_custom:applications'), {'status': Status.SHORTLISTED})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['applications']), 0)

    def test_admin_students_approval_workflow(self):
        """Verify admin can verify and approve or reject trainee candidates."""
        self.client.login(email='admin@nexthire.com', password='adminpassword')

        # 1. Verify trainee profile starts as pending approval
        self.assertEqual(self.stud_profile.approval_status, 'pending')

        # 2. Approve trainee candidate
        post_data = {
            'action': 'approve',
            'trainee_id': self.stud_profile.id
        }
        response = self.client.post(reverse('admin_custom:trainees'), data=post_data)
        self.assertEqual(response.status_code, 302)

        # Verify trainee is approved
        self.stud_profile.refresh_from_db()
        self.assertEqual(self.stud_profile.approval_status, 'approved')

        # 3. Reject trainee candidate
        post_data['action'] = 'reject'
        response = self.client.post(reverse('admin_custom:trainees'), data=post_data)
        self.assertEqual(response.status_code, 302)

        # Verify trainee is rejected
        self.stud_profile.refresh_from_db()
        self.assertEqual(self.stud_profile.approval_status, 'rejected')
