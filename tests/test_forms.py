# django_backend/tests/test_forms.py
"""
Unit tests for NextHire's Form structures.
Validates clean functions, unique entries validation, and validation of password matches.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
User = get_user_model()
from accounts.forms import StudentRegistrationForm, RecruiterRegistrationForm, LoginForm
from accounts.models import Role
from accounts.models import TraineeProfile
from recruiters.models import RecruiterProfile
from decimal import Decimal

class UserRegistrationFormTests(TestCase):
    def setUp(self):
        # Create an existing user to verify collision constraints
        self.existing_email = "lex@lexcorp.com"
        User.objects.create_user(email=self.existing_email, password="password321")

    def test_student_form_validation_happy_path(self):
        """Assert valid trainee registrations succeed and hold cleaned parameters."""
        form_data = {
            'name': 'Bruce Wayne',
            'email': 'bruce@trainee.com',
            'password': 'gotham_protector',
            'confirm_password': 'gotham_protector',
            'phone_number': '9999999999',
            'degree': 'MCA',
            'branch': 'Computer Science',
            'batch_code': 'B2026'
        }
        form = StudentRegistrationForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['email'], 'bruce@trainee.com')

    def test_student_form_validation_password_mismatch(self):
        """Assert that clean() raises a validation error when password inputs are not identical."""
        form_data = {
            'name': 'Clark Kent',
            'email': 'clark@trainee.com',
            'password': 'krypton_secret_1',
            'confirm_password': 'krypton_secret_different',
            'phone_number': '9999999999',
            'degree': 'MCA',
            'branch': 'Computer Science',
            'batch_code': 'B2026'
        }
        form = StudentRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("Passwords do not match!", form.non_field_errors())

    def test_student_form_validation_email_collision(self):
        """Assert clean_email triggers validation error on pre-registered logins."""
        form_data = {
            'name': 'Lex Luthor',
            'email': self.existing_email,
            'password': 'password_new',
            'confirm_password': 'password_new',
            'phone_number': '9999999999',
            'degree': 'MCA',
            'branch': 'Computer Science',
            'batch_code': 'B2026'
        }
        form = StudentRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
        self.assertEqual(form.errors['email'][0], "A user with this email address already exists.")
