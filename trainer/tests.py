from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from decimal import Decimal
from django.utils import timezone
from accounts.models import Role, TraineeProfile, RecruiterProfile, Course, TrainerProfile
from jobs.models import Job
from applications.models import Application, Status
from .models import CandidateRecommendation

User = get_user_model()

class PlacementOfficerModuleTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Seed Course
        self.course, _ = Course.objects.get_or_create(name='Python Full Stack')

        # Seed Trainer
        self.trainer = User.objects.create_user(
            email='trainer@nexthire.net',
            password='officerpassword',
            role=Role.TRAINER
        )
        self.officer_profile = TrainerProfile.objects.create(
            user=self.trainer,
            is_approved=True
        )
        self.officer_profile.courses_handled.add(self.course)

        # Seed Student
        self.stud_user = User.objects.create_user(
            email='trainee@nexthire.net',
            password='studentpassword',
            role=Role.TRAINEE
        )
        self.trainee_profile = TraineeProfile.objects.create(
            user=self.stud_user,
            usn='1RV22CS099',
            cgpa=Decimal('8.50'),
            approval_status='pending'
        )
        self.trainee_profile.courses.add(self.course)

        # Seed Recruiter & Job
        self.rec_user = User.objects.create_user(
            email='recruiter@nexthire.net',
            password='recruiterpassword',
            role=Role.RECRUITER
        )
        self.rec_profile = RecruiterProfile.objects.create(
            user=self.rec_user,
            company_name='Placement Test Partners',
            contact_email='hr@placementtest.com',
            is_approved_by_admin=True
        )
        self.job = Job.objects.create(
            recruiter=self.rec_profile,
            title='QA Engineer Intern',
            description='Test descriptions',
            min_cgpa_required=Decimal('7.00'),
            application_deadline=timezone.now().date() + timezone.timedelta(days=2),
            is_active=True
        )

    def test_unauthorized_access_redirects(self):
        """Verify that only placement trainers can access placement views."""
        # 1. Anonymous user
        response = self.client.get(reverse('trainer:dashboard'))
        self.assertEqual(response.status_code, 302)

        # 2. Student user
        self.client.login(email='trainee@nexthire.net', password='studentpassword')
        response = self.client.get(reverse('trainer:dashboard'))
        self.assertEqual(response.status_code, 302)
        self.client.logout()

    def test_placement_officer_dashboard_metrics(self):
        """Verify the dashboard shows correct counts of trainees and approval states."""
        self.client.login(email='trainer@nexthire.net', password='officerpassword')
        response = self.client.get(reverse('trainer:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_students'], 1)
        self.assertEqual(response.context['pending_students'], 1)
        self.assertEqual(response.context['approved_students'], 0)

    def test_student_approval_system(self):
        """Verify placement trainer can approve or reject candidate profiles."""
        self.client.login(email='trainer@nexthire.net', password='officerpassword')
        
        # Approve trainee
        response = self.client.post(reverse('trainer:approve'), {
            'trainee_id': self.trainee_profile.id,
            'action': 'approve'
        })
        self.assertEqual(response.status_code, 302)
        self.trainee_profile.refresh_from_db()
        self.assertEqual(self.trainee_profile.approval_status, 'approved')

        # Reject trainee
        response = self.client.post(reverse('trainer:approve'), {
            'trainee_id': self.trainee_profile.id,
            'action': 'reject'
        })
        self.assertEqual(response.status_code, 302)
        self.trainee_profile.refresh_from_db()
        self.assertEqual(self.trainee_profile.approval_status, 'rejected')

    def test_filter_system_job_applying(self):
        """Verify that ONLY approved trainees can apply for jobs."""
        # 1. Attempt while pending (should block)
        self.assertEqual(self.trainee_profile.approval_status, 'pending')
        self.client.login(email='trainee@nexthire.net', password='studentpassword')
        response = self.client.post(reverse('applications:apply', args=[self.job.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Application.objects.filter(trainee=self.trainee_profile, job=self.job).exists())
        self.client.logout()

        # 2. Approve Student
        self.client.login(email='trainer@nexthire.net', password='officerpassword')
        self.client.post(reverse('trainer:approve'), {
            'trainee_id': self.trainee_profile.id,
            'action': 'approve'
        })
        self.client.logout()

        # 3. Attempt while approved (should succeed)
        self.client.login(email='trainee@nexthire.net', password='studentpassword')
        response = self.client.post(reverse('applications:apply', args=[self.job.id]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Application.objects.filter(trainee=self.trainee_profile, job=self.job).exists())

    def test_candidate_recommendation(self):
        """Verify placement trainer can recommend approved trainees for active job openings."""
        # 1. Approve trainee first
        self.trainee_profile.approval_status = 'approved'
        self.trainee_profile.save()

        # 2. Post recommendation
        self.client.login(email='trainer@nexthire.net', password='officerpassword')
        response = self.client.post(reverse('trainer:recommend'), {
            'trainee_id': self.trainee_profile.id,
            'job_id': self.job.id,
            'comments': 'Top matching skills'
        })
        self.assertEqual(response.status_code, 302)
        
        # Verify recommendation in DB
        rec = CandidateRecommendation.objects.get(trainee=self.trainee_profile, job=self.job)
        self.assertEqual(rec.comments, 'Top matching skills')

    def test_course_officer_permission_isolation(self):
        """Verify that an trainer cannot approve or recommend a trainee if they don't share courses."""
        # Create a second course
        java_course, _ = Course.objects.get_or_create(name='Java Full Stack')
        
        # Create another trainee enrolled in Java Full Stack
        java_stud_user = User.objects.create_user(
            email='java_student@nexthire.net',
            password='studentpassword',
            role=Role.TRAINEE
        )
        java_student_profile = TraineeProfile.objects.create(
            user=java_stud_user,
            usn='1RV22CS100',
            cgpa=Decimal('9.00'),
            approval_status='pending'
        )
        java_student_profile.courses.add(java_course)
        
        self.client.login(email='trainer@nexthire.net', password='officerpassword')
        
        # 1. Attempt to approve Java trainee by Python trainer should fail (redirect and remain pending)
        response = self.client.post(reverse('trainer:approve'), {
            'trainee_id': java_student_profile.id,
            'action': 'approve'
        })
        self.assertEqual(response.status_code, 302)
        java_student_profile.refresh_from_db()
        self.assertEqual(java_student_profile.approval_status, 'pending')
        
        # 2. Attempt to recommend Java trainee by Python trainer should fail
        java_student_profile.approval_status = 'approved'
        java_student_profile.save()
        
        response = self.client.post(reverse('trainer:recommend'), {
            'trainee_id': java_student_profile.id,
            'job_id': self.job.id,
            'comments': 'Unauthorized recommendation'
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(CandidateRecommendation.objects.filter(trainee=java_student_profile, job=self.job).exists())

    def test_placement_jobs_view(self):
        """Verify placement trainer can view active jobs listing and eligible trainees."""
        self.trainee_profile.approval_status = 'approved'
        self.trainee_profile.save()

        self.client.login(email='trainer@nexthire.net', password='officerpassword')
        response = self.client.get(reverse('trainer:jobs'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'QA Engineer Intern')
        self.assertContains(response, self.trainee_profile.user.email)
