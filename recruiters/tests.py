# recruiters/tests.py
"""
Corporate partner recruitments process simulation test suite.
Verifies RBAC protection checkpoints, Profile adjustments, Job Publishing cycles, 
Screenings pipeline shifts, and Alert notifications dispatches.
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
User = get_user_model()
from django.utils import timezone
from datetime import datetime, timedelta

from accounts.models import Role
from recruiters.models import RecruiterProfile
from accounts.models import TraineeProfile
from jobs.models import Job
from applications.models import Application, Status
from interviews.models import Interview
from notifications.models import Notification

class RecruiterModuleTestCase(TestCase):
    def setUp(self):
        # 1. Establish recruiter auth credentials
        self.recruiter_user = User.objects.create_user(
            email='recruiter@intel.com',
            password='IntelPassword123',
            first_name='Albert',
            last_name='Core'
        )
        self.recruiter_profile = self.recruiter_user.profile
        self.recruiter_profile.role = Role.RECRUITER
        self.recruiter_profile.save()
        
        # Link RecruiterProfile
        self.recruiter_corp = RecruiterProfile.objects.create(
            user=self.recruiter_user,
            company_name="Intel Corporation",
            industry_domain="Semiconductor",
            company_website="https://intel.com",
            contact_email="talent@intel.com",
            is_approved_by_admin=True
        )

        # 2. Establish trainee candidate credentials
        self.trainee_user = User.objects.create_user(
            email='champion@campus.edu',
            password='StudentPass123',
            first_name='Srinivasan',
            last_name='Raman'
        )
        self.trainee_profile = self.trainee_user.profile
        self.trainee_profile.role = Role.TRAINEE
        self.trainee_profile.save()
        
        self.trainee_portfolio = TraineeProfile.objects.create(
            user=self.trainee_user,
            usn="1ST22CS192",
            cgpa=9.20,
            skills=["Python", "Django", "React"]
        )
        from accounts.models import Course
        self.course, _ = Course.objects.get_or_create(name="Computer Science")
        self.trainee_portfolio.courses.add(self.course)

        # 3. Establish common client instances
        self.client = Client()

    def test_unauthorized_student_access_blocks(self):
        """
        Phase 8: Protect recruiter URLs from candidates and guest users.
        """
        # Attempting unauthenticated access redirects to login
        response = self.client.get(reverse('recruiters:dashboard'))
        self.assertEqual(response.status_code, 302)
        
        # Login as trainee champion, should block/redirect
        self.client.login(email='champion@campus.edu', password='StudentPass123')
        response = self.client.get(reverse('recruiters:dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_authorized_recruiter_login_dashboard(self):
        """
        Tests dashboard loading and metrics counters.
        """
        self.client.login(email='recruiter@intel.com', password='IntelPassword123')
        response = self.client.get(reverse('recruiters:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Intel Corporation")

    def test_company_profile_update(self):
        """
        Phase 3: Company profile edit.
        """
        self.client.login(email='recruiter@intel.com', password='IntelPassword123')
        edit_url = reverse('recruiters:edit_profile')
        post_data = {
            'company_name': "Intel Labs India",
            'contact_email': "labs@intel.com",
            'industry_domain': "Artificial Intelligence",
            'company_website': "https://labs.intel.com",
            'about_company': "Pioneering the next gen silicon-designed neurochips."
        }
        
        response = self.client.post(edit_url, post_data)
        self.assertEqual(response.status_code, 302) # Redirects back to dashboard upon success
        
        self.recruiter_corp.refresh_from_db()
        self.assertEqual(self.recruiter_corp.company_name, "Intel Labs India")
        self.assertEqual(self.recruiter_corp.industry_domain, "Artificial Intelligence")

    def test_job_posting_crud(self):
        """
        Phase 4: Job Management Create, Edit, Toggle, and Delete.
        """
        self.client.login(email='recruiter@intel.com', password='IntelPassword123')
        
        # 1. Create Job Vacancy
        create_url = reverse('recruiters:job_create')
        deadline = timezone.now().date() + timedelta(days=30)
        post_data = {
            'title': "Firmware Architect Intern",
            'job_type': "INTERNSHIP",
            'location': "Bengaluru, IND",
            'salary_package': "60,000 INR/mo",
            'min_cgpa_required': '7.50',
            'raw_skills': "Asm, Python, C++",
            'description': "Configure low-level bios routines.",
            'is_active': True,
            'application_deadline': deadline.strftime('%Y-%m-%d'),
            'required_courses': [self.course.id]
        }
        
        response = self.client.post(create_url, post_data)
        self.assertEqual(response.status_code, 302)
        
        # Verify database insertion
        job = Job.objects.get(title="Firmware Architect Intern")
        self.assertEqual(job.recruiter, self.recruiter_corp)
        self.assertIn("Asm", job.skills_required)
        self.assertEqual(job.min_cgpa_required, 7.50)

        # 2. Edit Job Vacancy
        edit_url = reverse('recruiters:job_edit', args=[job.id])
        post_data['title'] = "Firmware Research Lead"
        post_data['raw_skills'] = "Asm, Python, Rust"
        
        response = self.client.post(edit_url, post_data)
        self.assertEqual(response.status_code, 302)
        job.refresh_from_db()
        self.assertEqual(job.title, "Firmware Research Lead")
        self.assertIn("Rust", job.skills_required)

        # 3. Toggle Activations
        toggle_url = reverse('recruiters:job_toggle', args=[job.id])
        response = self.client.get(toggle_url)
        self.assertEqual(response.status_code, 302)
        job.refresh_from_db()
        self.assertFalse(job.is_active)

    def test_applicants_workflows_and_notifications(self):
        """
        Phases 5, 6 & 7: Screening workflow status change and notifications dispatcher.
        """
        # Create a Job Posting beforehand
        deadline = timezone.now().date() + timedelta(days=20)
        job = Job.objects.create(
            recruiter=self.recruiter_corp,
            title="VLSI Design Engineer",
            description="Verilog RTL drafting vacancies",
            location="Bengaluru, IND",
            salary_package="16 LPA",
            skills_required=["Python", "React"],
            min_cgpa_required=8.00,
            is_active=True,
            application_deadline=deadline
        )
        
        # Candidate submits application
        application = Application.objects.create(
            trainee=self.trainee_portfolio,
            job=job,
            screener_score=85,
            status=Status.PENDING
        )

        self.client.login(email='recruiter@intel.com', password='IntelPassword123')

        # 1. Shortlist workflow transition
        shortlist_url = reverse('recruiters:update_status', args=[application.id, 'SHORTLISTED'])
        response = self.client.get(shortlist_url)
        self.assertEqual(response.status_code, 302)
        
        application.refresh_from_db()
        self.assertEqual(application.status, Status.SHORTLISTED)

        # Verify in-app notifications generated for the candidate trainee
        notif = Notification.objects.filter(user=self.trainee_user).first()
        self.assertIsNotNone(notif)
        self.assertIn("Shortlist", notif.title)
        self.assertEqual(notif.notification_type, Notification.Type.STATUS_UPDATE)

        # 2. Schedule Interview Round
        schedule_url = reverse('recruiters:schedule_interview', args=[application.id])
        interview_time = timezone.now() + timedelta(days=2)
        schedule_data = {
            'title': "VLSI Architecture Chat",
            'stage': 'TECHNICAL',
            'scheduled_at': interview_time.replace(microsecond=0).isoformat(),
            'platform': "Teams Call",
            'meet_url': "https://teams.microsoft.com/vlsi-intel"
        }
        
        response = self.client.post(schedule_url, schedule_data)
        self.assertEqual(response.status_code, 302)
        
        # Verify Interview instance matches
        interview = Interview.objects.filter(application=application).first()
        self.assertIsNotNone(interview)
        self.assertEqual(interview.platform, "Teams Call")
        self.assertEqual(interview.title, "VLSI Architecture Chat")
        
        # Verify status shifted to INTERVIEWING
        application.refresh_from_db()
        self.assertEqual(application.status, Status.INTERVIEWING)

        # Verify newly dispatched interview notification
        notifs = Notification.objects.filter(user=self.trainee_user, notification_type=Notification.Type.INTERVIEW_INVITATION)
        self.assertTrue(notifs.exists())

    def test_job_alert_notifications_and_badges(self):
        """Verify job posting generates notifications, which are cleared upon visiting target lists."""
        # 1. Create a placement trainer
        trainer_user = User.objects.create_user(
            email='officer_test@nexthire.net',
            password='officerpassword'
        )
        trainer_user.profile.role = Role.TRAINER
        trainer_user.profile.is_verified = True
        trainer_user.profile.save()
        from accounts.models import TrainerProfile
        TrainerProfile.objects.create(
            user=trainer_user,
            is_approved=True
        )

        self.client.login(email='recruiter@intel.com', password='IntelPassword123')
        
        # 2. Recruiter posts job
        create_url = reverse('recruiters:job_create')
        deadline = timezone.now().date() + timedelta(days=30)
        post_data = {
            'title': "Job Alert Test Intern",
            'job_type': "INTERNSHIP",
            'location': "Bengaluru, IND",
            'salary_package': "60,000 INR/mo",
            'min_cgpa_required': '7.50',
            'raw_skills': "Python",
            'description': "Notification testing.",
            'is_active': True,
            'application_deadline': deadline.strftime('%Y-%m-%d'),
            'required_courses': [self.course.id]
        }
        response = self.client.post(create_url, post_data)
        self.assertEqual(response.status_code, 302)

        # 3. Verify notifications generated
        trainee_notifs = Notification.objects.filter(user=self.trainee_user, notification_type=Notification.Type.JOB_ALERT, is_read=False)
        self.assertTrue(trainee_notifs.exists())

        trainer_notifs = Notification.objects.filter(user=trainer_user, notification_type=Notification.Type.JOB_ALERT, is_read=False)
        self.assertTrue(trainer_notifs.exists())

        # 4. Visit trainee feed, check notifications cleared
        self.client.login(email='champion@campus.edu', password='StudentPass123')
        response = self.client.get(reverse('jobs:feed'))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(trainee_notifs.filter(is_read=False).exists())

        # 5. Visit trainer jobs board, check notifications cleared
        self.client.login(email='officer_test@nexthire.net', password='officerpassword')
        response = self.client.get(reverse('trainer:jobs'))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(trainer_notifs.filter(is_read=False).exists())
