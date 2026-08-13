# django_backend/train_model.py
"""
Script to generate sample dataset, train RandomForestClassifier, and serialize using joblib.
"""

import os
import numpy as np
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

def generate_csv_dataset(filepath="placement_dataset.csv", num_records=1000):
    np.random.seed(42)
    
    # Feature ranges
    cgpa = np.random.uniform(6.0, 10.0, size=num_records)
    skills = np.random.randint(1, 12, size=num_records)
    internship = np.random.choice([0, 1], size=num_records, p=[0.6, 0.4])
    certifications = np.random.randint(0, 6, size=num_records)
    aptitude = np.random.randint(40, 100, size=num_records)
    projects = np.random.randint(0, 5, size=num_records)
    
    # logit math calculation
    logit = (
        2.5 * (cgpa - 7.5) +
        0.3 * skills +
        2.0 * internship +
        0.5 * certifications +
        0.05 * (aptitude - 60) +
        0.8 * projects -
        2.0
    )
    
    prob = 1 / (1 + np.exp(-logit))
    placed = (prob >= 0.5).astype(int)
    
    df = pd.DataFrame({
        'CGPA': np.round(cgpa, 2),
        'Skills': skills,
        'Internship': internship,
        'Certifications': certifications,
        'Aptitude': aptitude,
        'Projects': projects,
        'Placed': placed
    })
    
    df.to_csv(filepath, index=False)
    print(f"Generated sample dataset at {filepath} with {num_records} rows.")
    return df

def train_and_save_model(csv_path="placement_dataset.csv", model_path="placement_model.joblib"):
    if not os.path.exists(csv_path):
        df = generate_csv_dataset(csv_path)
    else:
        df = pd.read_csv(csv_path)
        
    X = df[['CGPA', 'Skills', 'Internship', 'Certifications', 'Aptitude', 'Projects']]
    y = df['Placed']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    clf = RandomForestClassifier(n_estimators=100, max_depth=6, random_state=42)
    clf.fit(X_train, y_train)
    
    y_pred = clf.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"RandomForestClassifier trained successfully. Accuracy: {acc:.2%}")
    
    joblib.dump(clf, model_path)
    print(f"Model saved to {model_path}")
    return clf

if __name__ == "__main__":
    train_and_save_model()
