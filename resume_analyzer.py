# django_backend/resume_analyzer.py
import os
import torch
import numpy as np
from transformers import AutoTokenizer, AutoModel
import re

# Global cache for the SBERT model
_TOKENIZER = None
_MODEL = None

def get_sbert_model():
    global _TOKENIZER, _MODEL
    if _TOKENIZER is None or _MODEL is None:
        try:
            # Using a tiny, fast SBERT model
            model_name = "sentence-transformers/all-MiniLM-L6-v2"
            _TOKENIZER = AutoTokenizer.from_pretrained(model_name)
            _MODEL = AutoModel.from_pretrained(model_name)
        except Exception as e:
            print(f"SBERT model loading failed: {e}. Semantic parsing will fall back to keyword-based matching.")
            _TOKENIZER = False
            _MODEL = False
    return _TOKENIZER, _MODEL

def mean_pooling(model_output, attention_mask):
    token_embeddings = model_output[0]
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)

def get_embedding(text, tokenizer, model):
    encoded_input = tokenizer(text, padding=True, truncation=True, max_length=512, return_tensors='pt')
    with torch.no_grad():
        model_output = model(**encoded_input)
    sentence_embeddings = mean_pooling(model_output, encoded_input['attention_mask'])
    return sentence_embeddings[0].numpy()

def compute_similarity(emb1, emb2):
    dot_product = np.dot(emb1, emb2)
    norm_emb1 = np.linalg.norm(emb1)
    norm_emb2 = np.linalg.norm(emb2)
    if norm_emb1 == 0 or norm_emb2 == 0:
        return 0.0
    return float(dot_product / (norm_emb1 * norm_emb2))

def analyze_resume_sbert(resume_text, job_title, job_description, required_skills):
    """
    Compares resume text with the job description and required skills using SBERT.
    Identifies matching skills, missing skills, weak sections, and improvement suggestions.
    """
    tokenizer, model = get_sbert_model()
    
    # Preprocess text
    resume_text_lower = resume_text.lower()
    
    matching_skills = []
    missing_skills = []
    
    # 1. Evaluate required skills
    if tokenizer and model:
        # Embed required skills and matching sentences in the resume
        sentences = [s.strip() for s in re.split(r'[.!?\n]', resume_text) if len(s.strip()) > 5]
        if sentences:
            try:
                # Get embeddings for sentences
                sentence_embs = [get_embedding(s, tokenizer, model) for s in sentences]
                
                for skill in required_skills:
                    skill_emb = get_embedding(skill, tokenizer, model)
                    max_sim = 0.0
                    for sent_emb in sentence_embs:
                        sim = compute_similarity(skill_emb, sent_emb)
                        if sim > max_sim:
                            max_sim = sim
                    
                    # Also check direct substring match as a fallback/reinforcement
                    if max_sim > 0.65 or re.search(r'\b' + re.escape(skill.lower()) + r'\b', resume_text_lower):
                        matching_skills.append(skill)
                    else:
                        missing_skills.append(skill)
            except Exception as e:
                print(f"Error during SBERT skills matching: {e}. Falling back to substring match.")
                for skill in required_skills:
                    if re.search(r'\b' + re.escape(skill.lower()) + r'\b', resume_text_lower):
                        matching_skills.append(skill)
                    else:
                        missing_skills.append(skill)
        else:
            missing_skills = list(required_skills)
    else:
        # Fallback to simple keyword/substring match if SBERT loading failed
        for skill in required_skills:
            if re.search(r'\b' + re.escape(skill.lower()) + r'\b', resume_text_lower):
                matching_skills.append(skill)
            else:
                missing_skills.append(skill)
                
    # 2. Analyze weak resume sections
    weak_sections = []
    sections = {
        "education": [r"education", r"academic", r"university", r"college", r"degree", r"btech", r"mtech", r"bca", r"mca"],
        "experience": [r"experience", r"work history", r"employment", r"internship", r"job", r"professional background"],
        "projects": [r"project", r"academic projects", r"personal projects", r"capstone"],
        "skills": [r"skills", r"technical skills", r"expertise", r"competencies", r"technologies"]
    }
    
    for sec_name, keywords in sections.items():
        found = False
        for kw in keywords:
            if re.search(r'\b' + kw + r'\b', resume_text_lower):
                found = True
                break
        if not found:
            weak_sections.append(sec_name.capitalize())
            
    # 3. Generate improvement suggestions
    suggestions = []
    
    if missing_skills:
        suggestions.append(f"Add projects or professional experience displaying work with: {', '.join(missing_skills)} to align with the role.")
        
    for ws in weak_sections:
        if ws == "Projects":
            suggestions.append("Your resume lacks a clear 'Projects' section. List 2-3 technical projects with detailed descriptions and GitHub links.")
        elif ws == "Experience":
            suggestions.append("Include an 'Experience' or 'Internships' section to outline practical projects or industry exposure.")
        elif ws == "Skills":
            suggestions.append("Structure a clear 'Technical Skills' or 'Key Competencies' section listing programming languages, frameworks, and databases.")
        elif ws == "Education":
            suggestions.append("Ensure your 'Education' history, degree domain, and graduation year are explicitly stated.")
            
    # SBERT similarity overview
    overall_similarity = 0.5
    if tokenizer and model:
        try:
            # Truncate descriptions and resumes to fit within token limits
            resume_emb = get_embedding(resume_text[:2000], tokenizer, model)
            job_emb = get_embedding(job_description[:2000], tokenizer, model)
            overall_similarity = compute_similarity(resume_emb, job_emb)
        except Exception as e:
            print(f"Error calculating overall similarity: {e}")
            
    if overall_similarity < 0.45:
        suggestions.append("The overall content of your resume shows low semantic match with the job description. Consider customizing your summary and profile keywords.")
    elif overall_similarity > 0.75:
        suggestions.append("Excellent semantic alignment! Your resume closely reflects the required competencies for this position.")
    else:
        suggestions.append("Moderate alignment. Tailor your resume descriptions to match the active terminology in the job description.")
        
    # Extra generic formatting suggestions
    if len(resume_text.split()) < 150:
        suggestions.append("Your resume text is very brief (under 150 words). Expand on your project architectures, technical contributions, and roles.")
        
    # 4. Generate Sentence-Level Rewrites & Additions
    MISSING_SKILL_TEMPLATES = {
        "java": "Developed backend modules and object-oriented components using Core Java.",
        "python": "Built automated data workflows, scripting solutions, and service APIs in Python.",
        "selenium webdriver": "Designed and maintained robust test automation frameworks using Selenium WebDriver with Java.",
        "selenium": "Designed and maintained robust test automation frameworks using Selenium WebDriver with Java.",
        "testng": "Structured and configured automation test suites utilizing TestNG for parallel execution.",
        "page object model (pom)": "Implemented Page Object Model (POM) design patterns to enhance framework maintainability.",
        "page object model": "Implemented Page Object Model (POM) design patterns to enhance framework maintainability.",
        "jenkins": "Configured and maintained CI/CD build pipelines using Jenkins for automated test execution.",
        "git": "Managed project source code control, branching strategies, and pull requests via Git.",
        "spring boot": "Developed microservices and RESTful API endpoints using Spring Boot framework.",
        "sql": "Wrote and optimized complex relational database queries and schemas using SQL.",
        "rest api": "Integrated and consumed RESTful Web Services to enable seamless data exchange.",
        "docker": "Containerized application microservices and environments using Docker for deployment.",
        "kubernetes": "Orchestrated and managed containerized deployments across Kubernetes clusters.",
        "aws": "Deployed and managed cloud infrastructure services on AWS (S3, EC2, RDS).",
        "manual testing": "Performed manual functional, regression, integration, and smoke testing across platforms.",
        "agile": "Collaborated effectively within Agile/Scrum development methodologies and sprints.",
    }

    # Split resume into sentences
    raw_sentences = [s.strip() for s in re.split(r'[.!?\n]', resume_text) if len(s.strip()) > 15]
    
    WEAK_SENTENCE_PATTERNS = [
        (r"\b(manual|testing|test)\b", "Functional testing exposure", "Designed and executed comprehensive functional and regression test scenarios, documenting bug reports and verifying software defects."),
        (r"\b(java)\b", "Core Java implementation", "Leveraged Core Java programming features and OOP design concepts to implement scalable application structures."),
        (r"\b(worked on|helped in|assisted)\b", "Active project ownership", "Led design, implementation, and deployment phases of target modules to optimize project execution workflows."),
        (r"\b(automation)\b", "Test Automation architecture", "Developed and automated regression suites using testing frameworks to minimize release cycle durations.")
    ]

    sentence_improvements = []
    used_sentences = set()

    for sent in raw_sentences:
        if sent in used_sentences:
            continue
        
        matched = False
        for pattern, reason, rewrite in WEAK_SENTENCE_PATTERNS:
            if re.search(pattern, sent.lower()):
                sentence_improvements.append({
                    "original": sent,
                    "suggestion": rewrite,
                    "reason": f"Upgrade to active voice for {reason}."
                })
                used_sentences.add(sent)
                matched = True
                break
                
        if len(sentence_improvements) >= 3:
            break

    # Fallback: if we didn't find enough, pick short sentences
    if len(sentence_improvements) < 2:
        short_sents = sorted([s for s in raw_sentences if s not in used_sentences and 20 <= len(s) <= 95], key=len)
        for sent in short_sents[:2]:
            sentence_improvements.append({
                "original": sent,
                "suggestion": "Expand this sentence with action verbs (e.g., 'Implemented', 'Designed'), tools used, and quantifiable results.",
                "reason": "Enhance descriptive depth and professional impact."
            })
            if len(sentence_improvements) >= 3:
                break

    return {
        "matching_skills": matching_skills,
        "missing_skills": missing_skills,
        "weak_sections": weak_sections,
        "suggestions": suggestions,
        "similarity_score": round(overall_similarity * 100, 1),
        "sentence_improvements": sentence_improvements,
        "missing_suggestions": [
            {
                "skill": skill,
                "suggested_text": MISSING_SKILL_TEMPLATES.get(skill.lower(), f"Demonstrated practical knowledge and technical proficiency in {skill} during project execution.")
            }
            for skill in missing_skills
        ]
    }
