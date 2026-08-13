# NextHire Launch Guide, Deployment Blueprint & Release Notes
This document is the master playbook for launching the NextHire platform into production on Google Cloud Platform (GCP) or AWS, compiling previous development efforts into a cohesive final release.

---

## I. Deployment Playbook (Production Architecture)

NextHire uses a modern, cost-efficient, full-stack containerized architecture:
- **Frontend Layer**: Static React/Vite layout served globally via a CDN.
- **Backend APIs Layer**: Python-Django server running in a Google Cloud Run container.
- **Database Engine**: Relational, managed Google Cloud SQL (MySQL instance).
- **Blob File Storage**: Secure Google Cloud Storage buckets for student resume files and profile photographs.

### 1. Database Setup Instructions
Locate the managed cloud SQL endpoint and configure authentication parameters inside `/django_backend/.env`:
1. Use Cloud SQL console to provision a MySQL 8.0 instance.
2. Create databases schema named `nexthire_placement_db`.
3. Provision user `nexthire_root_user` and assign a highly secure password.
4. Enforce SSL configuration to encrypt all database connections (`require_ssl = True`).

### 2. Static and Media Assets Setup
Django serves static and media assets via `gcloud` storage adapters or standard CDNs:
1. Initialize a storage bucket (e.g., `gs://nexthire-static-assets`).
2. Add bucket adapters to `/django_backend/nexthire/settings.py` using `django-storages`:
   ```python
   DEFAULT_FILE_STORAGE = 'storages.backends.gcloud.GoogleCloudStorage'
   STATICFILES_STORAGE = 'storages.backends.gcloud.GoogleCloudStorage'
   GS_BUCKET_NAME = 'nexthire-static-assets'
   ```
3. Run `python manage.py collectstatic --no-input` to compile and upload all static templates to the bucket.

### 3. Containerizing the Application
Use the lightweight Docker configuration below to package and run NextHire on Cloud Run or AWS ECS:

```dockerfile
# Use official slim Python runtime
FROM python:3.11-slim

# Prevent buffered streaming logs
ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Install system dependencies for MySQL and standard libraries
RUN apt-get update && apt-get install -y \
    build-essential \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY django_backend/ .

# Expose port and start gunicorn
EXPOSE 3000
CMD ["gunicorn", "--bind", "0.0.0.0:3000", "nexthire.wsgi:application", "--workers", "3"]
```

---

## II. Pre-Release Checklist (Go-Live Gate)

Execute these steps sequentially before the final production release:
1. **Turn Debug Mode Off**: Verify that `DJANGO_DEBUG` is set to `False` in `.env` to prevent Django from exposing raw development tracebacks.
2. **Apply Database Migrations**: Run `python manage.py migrate` to create all required database tables.
3. **Seed Database Tables**: Run administrative scripts to add default college courses, skills, and admin accounts.
4. **Train Baseline ML Model**: Run ML model initialization scripts (`python ml_engine/train_model.py`) to train and save the fallback placement predictor model before launching the server.
5. **Verify Firewall & Permissions**: Confirm firewall rules allow traffic between Cloud Run containers and database servers.

---

## III. Production Release Notes

**Project Title**: NextHire – Smart Placement & Recruitment Platform  
**Release Version**: v1.0.0-Stable  
**Release Timestamp**: June 11, 2026  

### New Implementations Summary
- **Placement Prediction Model**: Implemented a placement prediction model using a Scikit-Learn `RandomForestClassifier`. Calculates placement probability and confidence scores based on student profile attributes.
- **Candidate Matching & Ranking Engine**: Created automated algorithms that match student assets against job listings, generating a matching score from 1 to 100.
- **Career Counselor Chat**: Built an AI-powered conversational counselor that provides tips, suggests skills, and identifies career paths based on user interests.
- **Robust Testing Foundations**: Created a complete Django test suite containing:
  - `test_models.py` (Validating model fields and signals)
  - `test_views.py` (Validating permissions and redirections)
  - `test_urls.py` (Ensuring paths resolve correctly)
  - `test_forms.py` (Validating uniqueness and field-level rules)
  - `test_services.py` (Testing matching algorithms and predictions)
  - `test_integration.py` (Verifying the complete candidate-to-employment flow)

---

## IV. Post-Deployment Maintenance Plan

Ensure platform safety and reliability by establishing continuous maintenance cycles:
- **Relational Backups**: Schedule automated daily snapshots of the MySQL database. Retain production snapshots for up to 30 days.
- **ML Retraining Schedule**: Schedule Cron jobs to rebuild and retrain Scikit-Learn classifiers monthly using newly collected placement and application data.
- **Vulnerability Patch Updates**: Scan python pip dependencies daily for CVE vulnerabilities using automated tools (such as Snyk or Github Dependabot). Apply weekly security patches.
- **SLA Recovery and Verification**: Define high-priority response workflows for database drops or connection errors. System status heartbeats must execute every 30 seconds to alert site reliability engineers within 2 minutes of downtime.
