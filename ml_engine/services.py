# django_backend/ml_engine/services.py
"""
Unified Machine Learning Business logic algorithms directory.
Implements:
1. Candidate Ranking Engine against any Job requirements (Phase 3).
2. Personal Job Recommendation recommendation loops (Phase 4).
3. Skill Gap Diagnostic & curriculum advisors (Phase 5).
"""

from decimal import Decimal
from accounts.models import TraineeProfile
from jobs.models import Job
from ml_engine.predict import predict_placement_probability

def calculate_candidate_job_match(trainee: TraineeProfile, job: Job):
    """
    Computes a comprehensive match score (0 to 100) between a trainee and a job opening.
    """
    # 1. Skill Overlap scoring (60% of score)
    job_skills_lower = [s.lower().strip() for s in job.skills_required]
    student_skills_lower = [s.lower().strip() for s in trainee.skills]
    
    matched_skills = []
    missing_skills = []
    
    if job_skills_lower:
        for job_skill in job.skills_required:
            js_clean = job_skill.lower().strip()
            # Dynamic fuzzy overlap matching
            if any(js_clean in s or s in js_clean for s in student_skills_lower):
                matched_skills.append(job_skill)
            else:
                missing_skills.append(job_skill)
                
        skill_score = (len(matched_skills) / len(job_skills_lower)) * 100.0
    else:
        # Default skill score if job lists no specific requirements
        skill_score = 100.0
        
    # 2. Academic Alignment (20% of score)
    # Give full points for CGPA >= job min_cgpa, otherwise penalize proportion
    student_cgpa = float(trainee.cgpa)
    job_cgpa_min = float(job.min_cgpa_required)
    
    if student_cgpa >= job_cgpa_min:
        academic_score = 100.0
    else:
        # Heavily penalize academic gaps or mark as zero
        academic_score = max(0.0, (student_cgpa / max(0.1, job_cgpa_min)) * 80.0)
        
    # 3. Resume strength & Credentials score (20% of score)
    # Combines internships count and certs count
    internships_count = len(trainee.internships)
    certifications_count = len(trainee.certifications)
    projects_count = getattr(trainee, 'projects_count_derived', 1)  # Default index
    
    experience_score = min(100.0, (internships_count * 40.0) + (certifications_count * 20.0) + (projects_count * 20.0))
    
    # Weighted average sum
    raw_match_score = (0.60 * skill_score) + (0.20 * academic_score) + (0.20 * experience_score)
    
    # 4. Global clearance/eligibility check (CGPA cutoffs override)
    is_eligible = student_cgpa >= job_cgpa_min
    if not is_eligible:
        # Apply a critical eligibility penalty for raw ranking listing
        match_score = max(5.0, raw_match_score - 30.0)
    else:
        match_score = raw_match_score
        
    return {
        'match_score': round(match_score, 1),
        'is_eligible': is_eligible,
        'matched_skills': matched_skills,
        'missing_skills': missing_skills,
        'breakdown': {
            'skills_score': round(skill_score, 1),
            'academic_score': round(academic_score, 1),
            'experience_score': round(experience_score, 1)
        }
    }


def rank_candidates_for_job(job_id):
    """
    Queries all trainees and ranks them in descending order based on their match coefficients against a specific job role.
    """
    try:
        job = Job.objects.get(id=job_id)
    except Job.DoesNotExist:
        return []
        
    candidates = TraineeProfile.objects.filter(is_accredited_for_placement=True)
    ranked_list = []
    
    for trainee in candidates:
        evaluation = calculate_candidate_job_match(trainee, job)
        
        # Calculate dynamic placement probability for display in grid
        prob, confidence, _ = predict_placement_probability(
            cgpa=float(trainee.cgpa),
            skills_count=len(trainee.skills),
            internships_count=len(trainee.internships),
            certifications_count=len(trainee.certifications),
            aptitude_score=trainee.placement_readiness_score,
            projects_count=2  # typical default
        )
        
        ranked_list.append({
            'trainee_id': trainee.id,
            'student_name': trainee.user.get_full_name() or trainee.user.username,
            'branch': trainee.branch,
            'cgpa': trainee.cgpa,
            'skills': trainee.skills,
            'match_score': evaluation['match_score'],
            'is_eligible': evaluation['is_eligible'],
            'matched_skills': evaluation['matched_skills'],
            'missing_skills': evaluation['missing_skills'],
            'placement_probability': prob,
            'breakdown': evaluation['breakdown']
        })
        
    # Order by match score in descending order
    ranked_list.sort(key=lambda x: x['match_score'], reverse=True)
    
    # Add rank index
    for i, candidate in enumerate(ranked_list):
        candidate['rank'] = i + 1
        
    return ranked_list


def get_job_recommendations_for_student(trainee_id, limit=5):
    """
    Calculates candidate match scores against ALL active jobs and delivers organized, top-matching vacancies.
    """
    try:
        trainee = TraineeProfile.objects.get(id=trainee_id)
    except TraineeProfile.DoesNotExist:
        return [], []
        
    active_jobs = Job.objects.filter(is_active=True)
    recommendations = []
    
    for job in active_jobs:
        match_info = calculate_candidate_job_match(trainee, job)
        recommendations.append({
            'job': job,
            'match_score': match_info['match_score'],
            'is_eligible': match_info['is_eligible'],
            'matched_skills': match_info['matched_skills'],
            'missing_skills': match_info['missing_skills'],
            'breakdown': match_info['breakdown']
        })
        
    # Sort recommendations
    recommendations.sort(key=lambda x: x['match_score'], reverse=True)
    top_recs = recommendations[:limit]
    
    # Calculate a global "suggested skills to acquire" map from missing profiles on high matching jobs
    missing_frequency = {}
    for rec in recommendations[:10]:  # Evaluate high matches
        for m_skill in rec['missing_skills']:
            missing_frequency[m_skill] = missing_frequency.get(m_skill, 0) + 1
            
    # Sort and return top missing skills among popular matched options
    sorted_missing = [k for k, v in sorted(missing_frequency.items(), key=lambda item: item[1], reverse=True)]
    
    return top_recs, sorted_missing[:6]


def analyze_skill_gap(trainee_id, job_id):
    """
    Generates structured, clear instructions and gap resolution paths to help a trainee land a specific target role.
    """
    try:
        trainee = TraineeProfile.objects.get(id=trainee_id)
        job = Job.objects.get(id=job_id)
    except (TraineeProfile.DoesNotExist, Job.DoesNotExist):
        return None
        
    match_info = calculate_candidate_job_match(trainee, job)
    
    # Actionable guidance maps for common tech keywords
    curriculum_course_map = {
        'django': 'Python Django Full Stack Development course (MDN / Coursera)',
        'python': 'Advanced Python Object-Oriented Architectures (RealPython)',
        'react': 'React 19 & Next.js App Router Framework Guide (Vite ecosystem)',
        'mysql': 'Relational Schema Design & Query Performance Tuning (MySQL CrashCourse)',
        'postgresql': 'PostgreSQL High Performance Indexing & Clustering structures',
        'redis': 'Redis Caching Clusters and Serverless Storage architectures',
        'docker': 'Docker Containers & Kubernetes Microservice Deployment pipelines',
        'aws': 'AWS Cloud Practitioner certification & serverless functions',
        'git': 'GitHub Actions and CI/CD Automation environments',
        'scikit-learn': 'Scikit-Learn Machine Learning & Neural Network foundations'
    }
    
    recs_list = []
    for m_skill in match_info['missing_skills']:
        skill_clean = m_skill.lower().strip()
        matched_text = None
        for key, value in curriculum_course_map.items():
            if key in skill_clean or skill_clean in key:
                matched_text = value
                break
        if not matched_text:
            matched_text = f"Skill training bootcamps or open-source projects using {m_skill}"
        recs_list.append({
            'skill': m_skill,
            'suggestion': matched_text
        })
        
    return {
        'job_title': job.title,
        'company_name': job.recruiter.company_name,
        'match_score': match_info['match_score'],
        'is_eligible': match_info['is_eligible'],
        'matched_skills': match_info['matched_skills'],
        'missing_skills': match_info['missing_skills'],
        'breakdown': match_info['breakdown'],
        'actionable_steps': recs_list,
        'gpa_status': "Academic CGPA matches required cutoffs" if match_info['is_eligible'] else f"Academic Gap: Your score of {trainee.cgpa} is below jobcutoff parameter of {job.min_cgpa_required}."
    }
