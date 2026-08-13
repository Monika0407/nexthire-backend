# django_backend/ai_helpers.py
"""
AI helper functions using Google Gemini API.
"""

try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    genai = None
    HAS_GENAI = False

def setup_gemini():
    if not HAS_GENAI:
        return False
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
        return True
    return False

def analyze_resume(resume_text):
    """
    Analyzes resume text using Gemini API.
    Returns a dict with:
    - 'resume_score' (int)
    - 'extracted_skills' (list of str)
    - 'missing_skills' (list of str)
    - 'suggestions' (list of str)
    """
    has_api = setup_gemini()
    
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
        prompt = f"{system_instruction}\n\nResume text:\n{resume_text}"
        response = model.generate_content(prompt)
        result = json.loads(response.text.strip())
        return {
            "resume_score": int(result.get("resume_score", 70)),
            "extracted_skills": list(result.get("extracted_skills", [])),
            "missing_skills": list(result.get("missing_skills", [])),
            "suggestions": list(result.get("suggestions", []))
        }
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        return {
            "resume_score": 70,
            "extracted_skills": ["Technical Writing", "Core Engineering"],
            "missing_skills": ["Database Normalization", "System Design"],
            "suggestions": ["Ensure your contact info is clean.", "Structure your project listings with clear tech stacks."]
        }

def generate_mock_interview_question(role, history_dialogs=""):
    """
    Generates a technical interview question for a given role.
    """
    has_api = setup_gemini()
    system_instruction = (
        f"You are a senior technical interviewer conducting a mock interview for the role of {role}. "
        "Based on the dialogue history, ask the NEXT relevant technical question. "
        "Make it challenging, concise, and focused on practical technical scenarios. "
        "Return ONLY the question, nothing else."
    )
    
    if not has_api:
        questions = [
            "Can you explain the difference between a list and a tuple in Python, and when you would use each?",
            "What is Django Middleware, and how does it process requests and responses?",
            "How does database indexing work, and what are the trade-offs in terms of write operations?"
        ]
        import random
        return random.choice(questions)
        
    try:
        model = genai.GenerativeModel(model_name="gemini-2.5-flash")
        prompt = f"{system_instruction}\n\nDialogue History:\n{history_dialogs}\n\nAI Interviewer:"
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Error generating question: {e}")
        return "Explain how you would handle race conditions in Django database transactions."

def evaluate_mock_interview_answer(role, question, answer):
    """
    Evaluates a candidate's answer for a specific interview question.
    Returns a dict with 'score' (int) and 'feedback' (str).
    """
    has_api = setup_gemini()
    system_instruction = (
        f"You are a senior technical interviewer evaluating a mock interview for the role of {role}.\n"
        "Evaluate the candidate's answer to the following question. Return a JSON object with this schema:\n"
        "{\n"
        "  \"score\": 85,\n"
        "  \"feedback\": \"Your evaluation feedback here.\"\n"
        "}\n"
        "The score must be an integer between 0 and 100. Return ONLY the raw JSON block without markdown backticks."
    )
    
    if not has_api:
        return {
            "score": 85,
            "feedback": "Solid answer. You explained the concepts clearly, but you could have mentioned caching or indexing details to show deeper knowledge."
        }
        
    try:
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config={"response_mime_type": "application/json"}
        )
        prompt = f"{system_instruction}\n\nQuestion: {question}\nCandidate Answer: {answer}"
        response = model.generate_content(prompt)
        result = json.loads(response.text.strip())
        return {
            "score": int(result.get("score", 70)),
            "feedback": str(result.get("feedback", "Completed answer review."))
        }
    except Exception as e:
        print(f"Error evaluating answer: {e}")
        return {
            "score": 75,
            "feedback": "Answer submitted. The response shows good communication values, though technical details could be expanded."
        }

def get_career_guidance(trainee_profile, query, chat_history_str=""):
    """
    Generates a career guidance chatbot response.
    """
    has_api = setup_gemini()
    
    skills_str = ", ".join(trainee_profile.skills) if isinstance(trainee_profile.skills, list) else str(trainee_profile.skills)
    profile_context = (
        f"Candidate Name: {trainee_profile.user.get_full_name() or trainee_profile.user.email}\n"
        f"Degree: {trainee_profile.get_degree_display()} ({trainee_profile.branch})\n"
        f"CGPA: {trainee_profile.cgpa}/10.00\n"
        f"Skills: {skills_str}\n"
    )
    
    system_instruction = (
        "You are 'NextHire AI Assistant', a helpful and expert career counselor for college trainees. "
        "Use the trainee's profile context to give personalized, realistic, and encouraging career advice. "
        "Keep your response concise, structured, and easy to read (use bullet points where appropriate)."
    )
    
    if not has_api:
        if "skills" in query.lower():
            return "Based on your profile, you should learn: 1. Docker (for containerization), 2. Redis (for caching), 3. AWS (for deployment)."
        return "To suit your skills, you should target roles like Junior Django Developer, Backend Engineer, or Software Development Intern."
        
    try:
        model = genai.GenerativeModel(model_name="gemini-2.5-flash")
        prompt = f"{profile_context}\n\nChat History:\n{chat_history_str}\n\nStudent Query: {query}\n\nNextHire AI Assistant:"
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Error getting chatbot response: {e}")
        return "I am here to guide you. Try updating your profile's skills section so I can recommend tailored learning tracks."
