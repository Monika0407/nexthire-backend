# django_backend/resume_ai.py
"""
AI Resume Analyzer wrapper using Google Gemini API.
"""

import os
import json
import google.generativeai as genai

def setup_gemini():
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
        return True
    return False

def analyze_resume(resume_text):
    """
    Analyzes resume text using Gemini API.
    Returns a dict with keys:
    - 'resume_score' (int)
    - 'extracted_skills' (list of str)
    - 'missing_skills' (list of str)
    - 'suggestions' (list of str)
    """
    has_api = setup_gemini()
    
    # Prompt for structured response
    system_instruction = (
        "You are an expert AI Resume Analyst. Your job is to analyze the provided resume text "
        "and return a JSON object with the following schema:\n"
        "{\n"
        "  \"resume_score\": 75,\n"
        "  \"extracted_skills\": [\"Skill 1\", \"Skill 2\"],\n"
        "  \"missing_skills\": [\"Skill A\", \"Skill B\"],\n"
        "  \"suggestions\": [\"Suggestion 1\", \"Suggestion 2\"]\n"
        "}\n"
        "The resume_score should be a value from 0 to 100 based on standard industry requirements. "
        "Return ONLY the raw JSON block without markdown backticks."
    )
    
    if not has_api:
        # Standalone mock fallback
        print("GEMINI_API_KEY is not configured. Returning local mock analysis.")
        return {
            "resume_score": 80,
            "extracted_skills": ["Python", "Django", "SQL", "Git", "REST APIs"],
            "missing_skills": ["Docker", "Kubernetes", "AWS", "CI/CD Pipelines", "Redis"],
            "suggestions": [
                "Quantify your achievements, e.g., 'Optimized system queries, decreasing latency by 35%'.",
                "Add docker container deployment configurations for your projects.",
                "Register cloud certifications to raise recruitment indexing scores."
            ]
        }
        
    try:
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config={"response_mime_type": "application/json"}
        )
        
        # Combine system instruction and resume text
        prompt = f"{system_instruction}\n\nResume text:\n{resume_text}"
        response = model.generate_content(prompt)
        
        # Parse JSON
        result = json.loads(response.text.strip())
        return {
            "resume_score": int(result.get("resume_score", 70)),
            "extracted_skills": list(result.get("extracted_skills", [])),
            "missing_skills": list(result.get("missing_skills", [])),
            "suggestions": list(result.get("suggestions", []))
        }
    except Exception as e:
        print(f"Error calling Gemini API: {e}. Falling back to default data structure.")
        return {
            "resume_score": 70,
            "extracted_skills": ["Technical Writing", "Core Engineering"],
            "missing_skills": ["Database Normalization", "System Design"],
            "suggestions": ["Ensure your contact info is clean.", "Structure your project listings with clear tech stacks."]
        }
