# NextHire Enterprise Monitoring & Error Tracking Guide
This documentation defines standard operating procedures to deploy real-time telemetry, structured logging, and health checking metrics across NextHire nodes.

---

## 1. Django Structured Logging Configuration
Configure central formatting engines inside `/django_backend/nexthire/settings.py` to route log lines in real-time to standard stream outputs (`stdout`) in JSON-parsed blocks. This integrates smoothly with Cloud Logging layers (such as Google Cloud Logging/Stackdriver or AWS CloudWatch):

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json_verbose': {
            'format': '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}',
        },
    },
    'handlers': {
        'console_stream': {
            'class': 'logging.StreamHandler',
            'formatter': 'json_verbose',
        },
    },
    'root': {
        'handlers': ['console_stream'],
        'level': 'INFO',
    },
}
```

### Logging Rules
- **Authentication Events**: Log all user log-ins, log-outs, and role redirections at the `INFO` level.
- **Access Denials**: Log unauthorized access attempts (RBAC violations, CSRF failures) at the `WARNING` level, including the offending IP address, username, and path.
- **Third-Party API & ML Anomalies**: Log external network timeouts, database failures, and ML model loading errors at the `ERROR` level, including the error stack trace.

---

## 2. Real-Time Error Tracking (Sentry Integration)
Configure Sentry SDK to capture uncaught production exceptions and runtime warnings. Add the initialization code block to `/django_backend/nexthire/wsgi.py`:

```python
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

sentry_sdk.init(
    dsn="https://example_key@sentry.io/example_project_id",
    integrations=[DjangoIntegration()],
    traces_sample_rate=0.2, # sample 20% of requests for performance profiling
    send_default_pii=False # exclude student names and emails for privacy compliance
)
```

### Alerting Rules
- **Critical Alerts**: Trigger instant Slack or Email notifications to DevOps teams when SQL Database connection losses, Out-Of-Memory errors, or ML model failures occur.
- **Warning Triggers**: Route SMTP email notifications when third-party API latency exceeds 5.0 seconds.

---

## 3. Production Health Checking (Heartbeat API)
Verify application health and database connectivity using a dedicated, unauthenticated heartbeat endpoint (`/api/health/` or similar).

### Implementation Checklist
- Check for database access by running a simple query (e.g., `User.objects.count()`).
- Check that the active ML model is loaded and is ready for placement predictions.
- Verify that storage write/read permissions are functional in the media directories.

If all systems are healthy, return an HTTP 200 OK status in JSON format:
```json
{
  "status": "healthy",
  "timestamp": "2026-06-11T04:05:00Z",
  "services": {
    "mysql": "active",
    "ml_engine": "ready",
    "storage": "writable"
  }
}
```
If any system encounters an issue, return an HTTP 500 Internal Server Error status, detailing the unhealthy components to alert automated monitoring scripts.
