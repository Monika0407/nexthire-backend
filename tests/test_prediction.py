# django_backend/tests/test_prediction.py
"""
Unit tests for Placement Prediction Machine Learning System.
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
User = get_user_model()
from django.urls import reverse
from decimal import Decimal

from accounts.models import Role, TraineeProfile
from predict import predict_placement, predict_for_student

class PlacementPredictionTests(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Student credentials
        self.stud_user = User.objects.create_user(
            email='predict_student@nexthire.com',
            password='studentpassword',
            role=Role.TRAINEE
        )
        self.stud_profile = TraineeProfile.objects.create(
            user=self.stud_user,
            usn='1RV22CS999',
            cgpa=Decimal('8.50'),
            skills=['Python', 'Django', 'SQL'],
            internships=['Backend Dev Intern'],
            certifications=['AWS Cloud Practitioner'],
            placement_readiness_score=80,
            approval_status='approved'
        )
        
        # Recruiter credentials
        self.rec_user = User.objects.create_user(
            email='predict_recruiter@nexthire.com',
            password='recruiterpassword',
            role=Role.RECRUITER
        )

    def test_standalone_prediction_helper(self):
        """Verify the prediction helper computes expected outputs."""
        prob, prediction = predict_placement(
            cgpa=9.0,
            skills_count=8,
            internship_val=1,
            certifications_count=3,
            aptitude_score=85,
            projects_count=3
        )
        self.assertTrue(0.0 <= prob <= 1.0)
        self.assertIn(prediction, ["Placed", "Not Placed"])

    def test_predict_for_student_profile(self):
        """Verify prediction features mapping works for TraineeProfile instances."""
        prob, prediction = predict_for_student(self.stud_profile)
        self.assertTrue(0.0 <= prob <= 1.0)
        self.assertIn(prediction, ["Placed", "Not Placed"])

    def test_student_prediction_view_access(self):
        """Verify trainees can access the prediction page and unauthorized roles are blocked."""
        # 1. Anonymous access
        response = self.client.get(reverse('trainees:prediction'))
        self.assertEqual(response.status_code, 302)
        
        # 2. Recruiter access -> blocked (redirected)
        self.client.login(email='predict_recruiter@nexthire.com', password='recruiterpassword')
        response = self.client.get(reverse('trainees:prediction'))
        self.assertEqual(response.status_code, 302)
        self.client.logout()

        # 3. Authorized trainee access
        self.client.login(email='predict_student@nexthire.com', password='studentpassword')
        response = self.client.get(reverse('trainees:prediction'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Prediction Output")
        self.assertContains(response, "Academic CGPA")
        self.assertEqual(response.context['trainee'], self.stud_profile)
        self.assertTrue(0.0 <= response.context['probability'] <= 100.0)
