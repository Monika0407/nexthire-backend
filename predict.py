# django_backend/predict.py
"""
Prediction wrapper module. Loads the serialized RandomForest model and computes
placement probability and prediction labels for a given trainee profile.
"""

import os
import joblib
import numpy as np

def load_placement_model(model_path=None):
    if model_path is None:
        # Resolve path relative to this file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(current_dir, "placement_model.joblib")
        
    if not os.path.exists(model_path):
        # Auto-train if model does not exist yet to prevent crashes
        print(f"Model path {model_path} not found. Triggering auto-training...")
        from train_model import train_and_save_model
        return train_and_save_model(model_path=model_path)
        
    return joblib.load(model_path)

def predict_placement(cgpa, skills_count, internship_val, certifications_count, aptitude_score, projects_count):
    """
    Core prediction function.
    Inputs:
        - cgpa: float
        - skills_count: int
        - internship_val: int (0 or 1)
        - certifications_count: int
        - aptitude_score: int
        - projects_count: int
    Returns:
        - probability: float (0.0 to 1.0)
        - prediction_result: str ("Placed" or "Not Placed")
    """
    model = load_placement_model()
    
    # Input vector matches columns: 'CGPA', 'Skills', 'Internship', 'Certifications', 'Aptitude', 'Projects'
    features = np.array([[
        float(cgpa),
        int(skills_count),
        int(internship_val),
        int(certifications_count),
        int(aptitude_score),
        int(projects_count)
    ]])
    
    probability = float(model.predict_proba(features)[0][1])
    prediction = int(model.predict(features)[0])
    
    prediction_result = "Placed" if prediction == 1 else "Not Placed"
    
    return probability, prediction_result

def predict_for_student(trainee_profile):
    """
    Helper function to extract features from a Django TraineeProfile model instance
    and return the prediction parameters.
    """
    cgpa = float(trainee_profile.cgpa)
    
    # Check skills count from list
    skills = trainee_profile.skills
    skills_count = len(skills) if isinstance(skills, list) else 0
    
    # Check if has internship (Yes/No) -> 1 or 0
    internships = trainee_profile.internships
    internship_val = 1 if (isinstance(internships, list) and len(internships) > 0) else 0
    
    # Certifications count
    certs = trainee_profile.certifications
    certifications_count = len(certs) if isinstance(certs, list) else 0
    
    # Aptitude score
    aptitude_score = int(trainee_profile.placement_readiness_score)
    
    # Projects count (default to 2 if not explicitly present in model)
    projects_count = 2
    
    return predict_placement(cgpa, skills_count, internship_val, certifications_count, aptitude_score, projects_count)
