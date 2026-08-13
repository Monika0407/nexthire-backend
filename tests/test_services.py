# django_backend/tests/test_services.py
"""
Unit tests for NextHire's Business Logic and Machine Learning Services.
Covers matching scores, qualification cutoffs, candidate ranking, job recommendations,
and machine learning placement predictions.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
User = get_user_model()
from decimal import Decimal
from django.utils import timezone

from accounts.models import Role
from accounts.models import TraineeProfile
from recruiters.models import RecruiterProfile
from jobs.models import Job
from ml_engine.services import (
    calculate_candidate_job_match,
    rank_candidates_for_job,
    get_job_recommendations_for_student,
    analyze_skill_gap
)
from ml_engine.predict import predict_placement_probability


class MLSafetyAndRecommendationTests(TestCase):
    def setUp(self):
        # Setup users
        self.stud_user_1 = User.objects.create_user(email='bruce@nexthire.net', password='pwd', role=Role.TRAINEE)
        self.stud_user_1.first_name = "Bruce"
        self.stud_user_1.last_name = "Banner"
        self.stud_user_1.save()
        self.stud_user_2 = User.objects.create_user(email='tony@nexthire.net', password='pwd', role=Role.TRAINEE)
        self.stud_user_2.first_name = "Tony"
        self.stud_user_2.last_name = "Stark"
        self.stud_user_2.save()
        
        # Setup trainee 1: Great CGPA, some key skills
        self.student1 = TraineeProfile.objects.create(
            user=self.stud_user_1,
            usn="1RV22MC500",
            cgpa=Decimal("9.20"),
            skills=["Python", "Django", "MySQL"],
            certifications=["Cloud Practitioner"],
            internships=["Backend Intern at StarkLabs"]
        )
        self.student1.projects_count_derived = 3
        self.student1.save()
        
        # Setup trainee 2: Lower CGPA, different skills
        self.student2 = TraineeProfile.objects.create(
            user=self.stud_user_2,
            usn="1RV22MC501",
            cgpa=Decimal("6.10"),
            skills=["React", "Node.js", "Docker"],
            certifications=[],
            internships=[]
        )
        self.student2.projects_count_derived = 1
        self.student2.save()

        # Setup recruiter
        self.rec_user = User.objects.create_user(email='corporate_avengers@nexthire.net', password='pwd', role=Role.RECRUITER)
        self.recruiter = RecruiterProfile.objects.create(
            user=self.rec_user,
            company_name="S.H.I.E.L.D Technologies",
            contact_email="shield_recruiter@shield.gov",
            is_approved_by_admin=True
        )

        # Setup Job: High-standard Py-Django development
        self.job = Job.objects.create(
            recruiter=self.recruiter,
            title="Senior Django Core Developer",
            description="Seeking senior engineer fluent in Django, PostgreSQL, and Docker.",
            job_type=Job.JobType.FULL_TIME,
            location="New York, USA",
            salary_package="24 LPA",
            skills_required=["Python", "Django", "Docker", "PostgreSQL"],
            min_cgpa_required=Decimal("7.50"),
            application_deadline=timezone.now().date() + timezone.timedelta(days=20)
        )

    def test_candidate_job_match_calculation(self):
        """Verify match percentage, eligibility checking, and breakdown ratings."""
        # Evaluate Student 1 (Bruce): Expected match is higher due to high CGPA and matching Django/Python skills
        match_info_1 = calculate_candidate_job_match(self.student1, self.job)
        self.assertTrue(match_info_1['is_eligible'])
        self.assertIn("Python", match_info_1['matched_skills'])
        self.assertIn("Docker", match_info_1['missing_skills'])
        self.assertGreater(match_info_1['match_score'], 50.0)

        # Evaluate Student 2 (Tony): Uneligible due to CGPA < 7.50. Check eligibility gating penalty
        match_info_2 = calculate_candidate_job_match(self.student2, self.job)
        self.assertFalse(match_info_2['is_eligible'])
        #Tony's score should have been penalized/reduced
        self.assertLess(match_info_2['match_score'], 55.0)

    def test_candidate_ranking_for_job(self):
        """Assert candidate ranking sorts candidates in correct match order and applies ranking indices."""
        rankings = rank_candidates_for_job(self.job.id)
        
        self.assertEqual(len(rankings), 2)
        # Bruces' match score should be higher than Tonys' (Bruce has python/django skills + 9.20 cgpa + eligibility)
        self.assertEqual(rankings[0]['trainee_id'], self.student1.id)
        self.assertEqual(rankings[0]['rank'], 1)
        self.assertEqual(rankings[1]['trainee_id'], self.student2.id)
        self.assertEqual(rankings[1]['rank'], 2)

    def test_job_recommendation_and_skill_gap_analysis(self):
        """Assert and test recommended jobs and diagnostic steps."""
        top_recs, missing_skills = get_job_recommendations_for_student(self.student1.id)
        # self.job is active, so we should get it as a recommendation
        self.assertEqual(len(top_recs), 1)
        self.assertEqual(top_recs[0]['job'].id, self.job.id)
        self.assertIn("Docker", missing_skills)

        # Diagnostic checking
        gap_report = analyze_skill_gap(self.student1.id, self.job.id)
        self.assertIsNotNone(gap_report)
        self.assertEqual(gap_report['job_title'], self.job.title)
        # Check that there's an actionable course recommendation for Docker
        has_docker_suggestion = any(step['skill'] == "Docker" for step in gap_report['actionable_steps'])
        self.assertTrue(has_docker_suggestion)

    def test_placement_probability_prediction(self):
        """Validate ML probability predict, ensuring it gracefully handles fallbacks."""
        prob, confidence, version = predict_placement_probability(
            cgpa=8.8,
            skills_count=4,
            internships_count=1,
            certifications_count=2,
            aptitude_score=85,
            projects_count=3
        )
        # Probabilities should range between 0 and 1
        self.assertTrue(0.0 <= prob <= 1.0)
        # Confidence score should represent realistic percentage
        self.assertTrue(50.0 <= confidence <= 100.0)
        self.assertIsNotNone(version)
