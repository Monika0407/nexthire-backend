# NextHire Performance, Sizing & Scalability Benchmarks
This benchmark specification outlines key performance thresholds and load standards to guarantee that NextHire remains responsive during peak placement drives.

---

## 1. Page Load Budgets & Responsiveness
Performance targets are measured under simulated high-load scenarios:

| Metric | Target | Warning Threshold | Critical Alert Level |
| :--- | :--- | :--- | :--- |
| **First Contentful Paint (FCP)** | < 1.0s | 1.8s | > 2.5s |
| **Largest Contentful Paint (LCP)** | < 2.0s | 3.0s | > 4.5s |
| **Interaction to Next Paint (INP)** | < 100ms | 200ms | > 350ms |
| **API response latency** | < 150ms | 300ms | > 500ms |
| **ML prediction calculations** | < 120ms | 250ms | > 400ms |
| **AI prompt response (streaming)**| < 2.0s first chunk | 3.5s | > 5.0s |

---

## 2. Database (Django ORM) Optimization Codes
- [ ] **Prevent N+1 Queries**: Always use `select_related` for single-relationship lookups (such as `Application.student` or `Job.recruiter`) and `prefetch_related` for multi-relationship collections (such as `StudentProfile.skills` or `User.notifications`). This combines multiple queries into single, efficient executions.
- [ ] **Index Configuration Optimization**: Ensure indexes are created for all fields frequently used in filters, joins, or sort order (for example, `StudentProfile.cgpa`, `Application.status`, and `Notification.created_at`).
- [ ] **Paginated Output Streams**: Enforce paginated results on all feed arrays (such as the job feed or candidate tables). Limit page frames to 20 record offsets per requests load.
- [ ] **Chunked Data Processing**: When executing bulk operations (such as compiling statistical aggregates), process records in chunks using `iterator()` to optimize memory usage.

---

## 3. Cache Management & Pre-Calculations
- [ ] **Database Result Caching**: Configure Redis as the primary caching backend. Store active job listings and general system configurations using standard timeout loops (e.g., up to 2 hours of persistent cache).
- [ ] **Pre-Baked Match Scores**: Run matching scoring algorithms during off-peak windows or when a profile or job listing is updated. Avoid recalculating match scores dynamically during high-traffic browsing.
- [ ] **Scale-to-Zero Storage Policies**: Compress historical prediction logs and job matching metrics into static analytical tables weekly to keep operational database tables small and performant.

---

## 4. Background Task Systems (Asynchronous Operations)
- [ ] **Non-Blocking Email Despatches**: SMTP email operations must run asynchronously using background workers (such as Django Celery or Huey) rather than executing synchronously in the main HTTP request-response cycle.
- [ ] **Model Retraining Pipelines**: Schedule ML model training jobs during low-traffic windows (e.g., nightly at 02:00 UTC). Training sessions must not impact active student or recruiter portals.
- [ ] **Media Compression**: Compress all student profile pictures and docx assets automatically at the upload gateway.
