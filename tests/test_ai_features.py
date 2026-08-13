# django_backend/tests/test_ai_features.py
"""
Unit tests for Gemini AI Integration features (Resume Analyzer, Mock Interview, Chatbot).
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
User = get_user_model()
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from decimal import Decimal

from accounts.models import Role, TraineeProfile

class AIFeaturesTests(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Student credentials
        self.stud_user = User.objects.create_user(
            email='ai_student@nexthire.com',
            password='studentpassword',
            role=Role.TRAINEE
        )
        self.stud_profile = TraineeProfile.objects.create(
            user=self.stud_user,
            usn='1RV22CS777',
            cgpa=Decimal('8.00'),
            skills=['Python', 'HTML'],
            internships=[],
            certifications=[],
            placement_readiness_score=70,
            approval_status='approved'
        )
        
        # Recruiter credentials
        self.rec_user = User.objects.create_user(
            email='ai_recruiter@nexthire.com',
            password='recruiterpassword',
            role=Role.RECRUITER
        )

    def test_unauthorized_access(self):
        """Verify recruiters and anonymous users cannot access AI endpoints."""
        urls = [
            reverse('trainees:resume_analysis'),
            reverse('trainees:interview'),
            reverse('trainees:chatbot'),
        ]
        for url in urls:
            # 1. Anonymous redirected
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            
            # 2. Recruiter redirected
            self.client.login(email='ai_recruiter@nexthire.com', password='recruiterpassword')
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.client.logout()

    def test_resume_analysis_view(self):
        """Verify the AI resume analysis page loads and handles file upload diagnostics."""
        self.client.login(email='ai_student@nexthire.com', password='studentpassword')
        
        # 1. GET page
        response = self.client.get(reverse('trainees:resume_analysis'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AI Resume Analyzer")

        # 2. POST invalid file extension
        bad_file = SimpleUploadedFile("resume.txt", b"my resume text", content_type="text/plain")
        response = self.client.post(reverse('trainees:resume_analysis'), {'resume_file': bad_file})
        self.assertEqual(response.status_code, 302)
        
        # 3. POST dummy pdf file (PyMuPDF try-catch handles invalid pdf format without crashing)
        dummy_pdf = SimpleUploadedFile("resume.pdf", b"dummy pdf text content", content_type="application/pdf")
        response = self.client.post(reverse('trainees:resume_analysis'), {'resume_file': dummy_pdf})
        self.assertEqual(response.status_code, 200)

    def test_mock_interview_simulation_loop(self):
        """Verify the mock interview view runs role initialization and loops round cycles."""
        self.client.login(email='ai_student@nexthire.com', password='studentpassword')
        
        # 1. GET step 0 - choose role
        response = self.client.get(reverse('trainees:interview'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Initialize Simulation Session")

        # 2. POST choose role (initiates round 1)
        response = self.client.post(reverse('trainees:interview'), {'role_title': 'Python Developer'})
        self.assertEqual(response.status_code, 302)
        
        # Session state should be updated to step 1
        self.assertEqual(self.client.session['interview_step'], 1)
        self.assertEqual(self.client.session['interview_role'], 'Python Developer')
        self.assertEqual(len(self.client.session['interview_questions']), 1)

        # 3. GET step 1 - show question
        response = self.client.get(reverse('trainees:interview'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Round 1 of 3")

        # 4. POST answer for round 1 -> moves to round 2
        response = self.client.post(reverse('trainees:interview'), {'answer': 'Python has lists and tuples.'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session['interview_step'], 2)
        self.assertEqual(len(self.client.session['interview_answers']), 1)

    def test_chatbot_guidance_view(self):
        """Verify chatbot guidance chat sessions load greetings and process career queries."""
        self.client.login(email='ai_student@nexthire.com', password='studentpassword')
        
        # 1. GET chatbot guidance
        response = self.client.get(reverse('trainees:chatbot'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AI Career Counselor Chatbot")
        
        # Greeting should be initialized in session
        self.assertTrue(len(self.client.session['student_chat_history']) > 0)
        self.assertEqual(self.client.session['student_chat_history'][0]['role'], 'ai')

        # 2. POST query
        response = self.client.post(reverse('trainees:chatbot'), {'query': 'What skills should I learn?'})
        self.assertEqual(response.status_code, 302)
        
        # Chat history should contain user query and AI response
        history = self.client.session['student_chat_history']
        self.assertEqual(history[1]['role'], 'user')
        self.assertEqual(history[1]['content'], 'What skills should I learn?')
        self.assertEqual(history[2]['role'], 'ai')
