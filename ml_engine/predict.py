# django_backend/ml_engine/predict.py
"""
Prediction Helper utilities.
Loads serialized RandomForestClassifiers via joblib, processes incoming profiles,
and computes placement probabilities alongside model consensus confidence metrics.
"""

import os
import joblib
import numpy as np

# Import Django-level references inside safe try-blocks
try:
    from ml_engine.models import MLModelMetadata
except ImportError:
    MLModelMetadata = None

def get_active_model():
    """
    Finds the active model path and metadata. 
    If no models are found, a default model is trained on-the-fly to prevent service crashes.
    """
    model_dir = os.path.join(os.path.dirname(__file__), 'saved_models')
    os.makedirs(model_dir, exist_ok=True)
    
    active_version = None
    model_path = None
    
    # Try querying MySQL registered models first if available
    if MLModelMetadata is not None:
        try:
            active_model_record = MLModelMetadata.objects.filter(is_active=True).first()
            if active_model_record:
                active_version = active_model_record.version
                model_path = active_model_record.model_file_path
        except Exception:
            pass
            
    # Fallback to loading filesystem files
    if not model_path or not os.path.exists(model_path):
        files = [f for f in os.listdir(model_dir) if f.startswith('placement_clf_') and f.endswith('.joblib')]
        if files:
            # Load the latest modified file
            latest_file = max(files, key=lambda x: os.path.getmtime(os.path.join(model_dir, x)))
            model_path = os.path.join(model_dir, latest_file)
            active_version = latest_file.replace('placement_clf_', '').replace('.joblib', '')
        else:
            # Strictly auto-train a default version if none are compiled to prevent startup crashes (as per guidelines!)
            print("No saved models found in filesystem directories. Running default training execution...")
            from ml_engine.train_model import train_placements_model, train_test_split
            model_path, metrics = train_placements_model(version_slug="fallback_v1")
            active_version = "fallback_v1"
            
            # Persist metadata record in cloud DB if available
            if MLModelMetadata is not None:
                try:
                    MLModelMetadata.objects.all().update(is_active=False)
                    MLModelMetadata.objects.create(
                        version="fallback_v1",
                        algorithm_name="RandomForestClassifier",
                        accuracy=metrics['accuracy'],
                        precision=metrics['precision'],
                        recall=metrics['recall'],
                        f1_score=metrics['f1_score'],
                        model_file_path=model_path,
                        features_used=list(metrics['feature_importances'].keys()),
                        is_active=True,
                        description="Auto-generated fallback baseline model."
                    )
                except Exception as e:
                    print(f"Failed to save fallback metadata: {e}")

    # Load and cache joblib binaries
    try:
        model_object = joblib.load(model_path)
        return model_object, active_version
    except Exception as err:
        print(f"Error deserializing model from {model_path}: {err}")
        return None, None


def calculate_consensus_confidence(model, feature_vector):
    """
    Calculates consensus level across all individual trees inside a RandomForest model.
    A high consensus yields a high confidence score. Variance in tree votes lowers confidence.
    """
    if not hasattr(model, 'estimators_'):
        return 85.0  # Constant fallback if model lacks estimator ensembles
        
    predictions_forest = []
    for estimator in model.estimators_:
        # Collect positive-class probability of every individual tree in the ensemble
        prob = estimator.predict_proba(feature_vector)[0][1]
        predictions_forest.append(prob)
        
    # Consensus std dev ranges from 0.0 (unyielding agreement) to 0.5 (perfect chaos)
    consensus_std = np.std(predictions_forest)
    
    # Normalize consensus confidence metrics: maps [0.0, 0.5] std dev onto [99.0, 50.0]% confidence spread
    consensus_pct = float(100.0 - (consensus_std * 98.0))
    return np.clip(consensus_pct, 52.0, 99.5)


def predict_placement_probability(cgpa, skills_count, internships_count, certifications_count, aptitude_score, projects_count):
    """
    Accepts profile matrices, feeds active classifier, and responds with outputs.
    """
    clf, version = get_active_model()
    if not clf:
        return 0.50, 50.0, "None Loaded"
        
    # Align features in standard shape
    feature_arr = np.array([[
        float(cgpa),
        int(skills_count),
        int(internships_count),
        int(certifications_count),
        int(aptitude_score),
        int(projects_count)
    ]])
    
    # Predict probabilities
    probs = clf.predict_proba(feature_arr)
    placement_prob = float(probs[0][1])
    
    # Dynamic confidence calculations
    confidence = calculate_consensus_confidence(clf, feature_arr)
    
    return placement_prob, confidence, version
