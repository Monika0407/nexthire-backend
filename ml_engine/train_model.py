# django_backend/ml_engine/train_model.py
"""
Placement Prediction Model training pipeline file.
Generates balanced synthetic training data, fits scikit-learn RandomForestClassifier,
evaluates performance metrics, and saves binary outputs using joblib.
"""

import os
import json
import numpy as np
import pandas as pd
from datetime import datetime
import joblib

# Framework utilities
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix

def generate_placement_dataset(num_records=1500, random_seed=42):
    """
    Generates highly-realistic, balanced synthetic dataset for trainee placement evaluation.
    Ties variables to typical trainee profiles.
    """
    np.random.seed(random_seed)
    
    # Feature ranges
    cgpa = np.random.uniform(5.5, 9.8, size=num_records)
    skills_count = np.random.randint(1, 15, size=num_records)
    internships = np.random.randint(0, 3, size=num_records)
    certifications = np.random.randint(0, 5, size=num_records)
    aptitude_score = np.random.randint(40, 100, size=num_records)
    projects = np.random.randint(0, 5, size=num_records)
    
    # Mathematical logit probability structure
    # Higher scores globally boost probability. Coefficients set typical industry values:
    # CGPA weight: 1.8, Internships: 1.5, Projects: 0.9, Aptitude: 0.04, Skills: 0.15, Certs: 0.3
    logit = (
        1.8 * (cgpa - 7.0) +
        1.5 * internships +
        0.9 * projects +
        0.04 * (aptitude_score - 60) +
        0.15 * skills_count +
        0.3 * certifications -
        1.8  # Intercept
    )
    
    # Convert logit to probability
    probability = 1 / (1 + np.exp(-logit))
    
    # Introduce controlled noise to simulate human anomalies
    noise = np.random.normal(0, 0.1, size=num_records)
    final_prob = np.clip(probability + noise, 0.0, 1.0)
    
    # Set threshold (0.5) to determine placement success target
    placed = (final_prob >= 0.5).astype(int)
    
    data = pd.DataFrame({
        'cgpa': cgpa,
        'skills_count': skills_count,
        'internships_count': internships,
        'certifications_count': certifications,
        'aptitude_score': aptitude_score,
        'projects_count': projects,
        'placed': placed
    })
    
    return data

def train_placements_model(dataset_df=None, version_slug=None, description=""):
    """
    Fits and saves a RandomForest model based on df or falls back to synthetic generation.
    Returns metrics dict and output locations.
    """
    if dataset_df is None:
        dataset_df = generate_placement_dataset()
        
    print(f"Dataset summary: {len(dataset_df)} rows. Positive placements index: {dataset_df['placed'].mean():.1%}")
    
    # Define features and labels
    feature_cols = ['cgpa', 'skills_count', 'internships_count', 'certifications_count', 'aptitude_score', 'projects_count']
    X = dataset_df[feature_cols]
    y = dataset_df['placed']
    
    # Split training vs validation datasets
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.20, random_state=42, stratify=y)
    
    # Instantiate Forest models
    clf = RandomForestClassifier(
        n_estimators=100,
        max_depth=8,
        min_samples_split=4,
        random_state=42,
        class_weight='balanced'
    )
    
    # Train
    clf.fit(X_train, y_train)
    
    # Predict
    y_pred = clf.predict(X_test)
    y_proba = clf.predict_proba(X_test)[:, 1]
    
    # Calculate performance metrics
    accuracy = float(accuracy_score(y_test, y_pred))
    precision = float(precision_score(y_test, y_pred))
    recall = float(recall_score(y_test, y_pred))
    f1 = float(f1_score(y_test, y_pred))
    
    cf_matrix = confusion_matrix(y_test, y_pred).tolist()
    
    # Setup directory structure for saved models
    model_dir = os.path.join(os.path.dirname(__file__), 'saved_models')
    os.makedirs(model_dir, exist_ok=True)
    
    if not version_slug:
        version_slug = f"v_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
    model_filename = f"placement_clf_{version_slug}.joblib"
    model_path = os.path.join(model_dir, model_filename)
    
    # Serialize model binary
    joblib.dump(clf, model_path)
    
    # Feature importances
    importances = dict(zip(feature_cols, clf.feature_importances_.tolist()))
    
    metrics = {
        'version': version_slug,
        'algorithm': 'RandomForestClassifier',
        'trained_at': datetime.now().isoformat(),
        'dataset_rows': len(dataset_df),
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1_score': f1,
        'confusion_matrix': cf_matrix,
        'feature_importances': importances,
        'description': description
    }
    
    # Save accompanying metrics json log
    metrics_path = os.path.join(model_dir, f"metrics_{version_slug}.json")
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=4)
        
    print(f"Model successfully trained! Accuracy: {accuracy:.2%}, Model serialized to {model_path}")
    
    return model_path, metrics

if __name__ == "__main__":
    path, results = train_placements_model()
    print(json.dumps(results, indent=2))
