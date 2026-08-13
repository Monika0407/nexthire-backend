# django_backend/tests/test_urls.py
"""
Unit tests for NextHire's URL Routing architecture.
Validates name-to-view reversibility and resolves named paths across sub-apps.
"""

from django.test import SimpleTestCase
from django.urls import reverse, resolve
from accounts.views import student_register_view, recruiter_register_view, login_view, role_routing_view, logout_view
from jobs.views import active_jobs_feed_view, post_new_job_view
from interviews.views import student_interview_dashboard_view, recruiter_interview_dashboard_view

class AccountsUrlTests(SimpleTestCase):
    def test_auth_urls_resolve(self):
        """Assert that accounts authentication URLs map correctly to their designated views."""
        # Student Registration url check
        self.assertEqual(reverse('accounts:register_student'), '/accounts/register/trainee/')
        self.assertEqual(resolve('/accounts/register/trainee/').func, student_register_view)
        
        # Recruiter Registration url check
        self.assertEqual(reverse('accounts:register_recruiter'), '/accounts/register/recruiter/')
        self.assertEqual(resolve('/accounts/register/recruiter/').func, recruiter_register_view)
        
        # Login url check
        self.assertEqual(reverse('accounts:login'), '/accounts/login/')
        self.assertEqual(resolve('/accounts/login/').func, login_view)
        
        # Role routing gateway check
        self.assertEqual(reverse('accounts:role_routing'), '/accounts/route-gateway/')
        self.assertEqual(resolve('/accounts/route-gateway/').func, role_routing_view)
        
        # Logout url check
        self.assertEqual(reverse('accounts:logout'), '/accounts/logout/')
        self.assertEqual(resolve('/accounts/logout/').func, logout_view)


class JobsUrlTests(SimpleTestCase):
    def test_job_urls_resolve(self):
        """Assert that jobs listing URLs map to feed and publishing view functions."""
        # Active feeds list
        self.assertEqual(reverse('jobs:feed'), '/jobs/feed/')
        self.assertEqual(resolve('/jobs/feed/').func, active_jobs_feed_view)
        
        # Publish jobs path
        self.assertEqual(reverse('jobs:publish'), '/jobs/publish/')
        self.assertEqual(resolve('/jobs/publish/').func, post_new_job_view)


class InterviewsUrlTests(SimpleTestCase):
    def test_interview_urls_resolve(self):
        """Assert that interview pathways resolve to corresponding trainee/recruiter boards."""
        # Student evaluation board
        self.assertEqual(reverse('interviews:student_dashboard'), '/interviews/dashboard/trainee/')
        self.assertEqual(resolve('/interviews/dashboard/trainee/').func, student_interview_dashboard_view)
        
        # Recruiter corporate board
        self.assertEqual(reverse('interviews:recruiter_dashboard'), '/interviews/dashboard/recruiter/')
        self.assertEqual(resolve('/interviews/dashboard/recruiter/').func, recruiter_interview_dashboard_view)
