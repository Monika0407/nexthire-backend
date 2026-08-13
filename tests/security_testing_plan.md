# NextHire Cybersecurity & Gated Defense Testing Plan
This testing manual defines verification cycles to harden the NextHire application against malicious exploits, credential theft, and unauthorized access.

---

## 1. Authentication & Session Defense
- [ ] **Password Strength Checks**: Verify that registration rules enforce strong passwords (minimum 10 characters, upper/lower cases, numerical values, and keyboard symbols).
- [ ] **Brute-Force Attack Mitigation**: Confirm login endpoints are protected by rate-limit throttling (e.g., maximum 5 login attempts within a 15-minute window from a single IP address).
- [ ] **Session Cookie Protection**: Ensure session cookies are flagged with `HttpOnly` (to block access from JavaScript cross-site scripting), `Secure` (to ensure transmission occurs only over SSL/TLS), and `SameSite=Lax` (to mitigate cross-site request forgery).
- [ ] **Session Lifespan Restrictions**: Verify that sessions auto-terminate after 30 minutes of user inactivity, requiring re-authentication to restore access.

---

## 2. Authorization Boundaries (Role-Based Access Gating - RBAC)
- [ ] **Direct URL Exploitation Mitigation**: Verify that the system blocks attempts to access administrative pages (such as `/admin/` or `/recruiters/dashboard/`) directly by typing the URL as an unauthenticated user, or as a user with a `STUDENT` role.
- [ ] **Cross-Owner Record Safety**: Confirm that a student cannot view or modify another candidate's profile, resume, or interview results by altering URL parameters (such as `/students/profile/Edit/?id=14`). Each view must validate records against `request.user`.
- [ ] **Feature Gating**: Ensure that actions reserved for specific roles are blocked for all other roles. For example, trying to post a job via `/jobs/publish/` as a student must return an HTTP 403 Forbidden error or redirect to an access denial page.

---

## 3. Vulnerability Protection
- [ ] **SQL Injection Defense**: Confirm that all database operations use Django's ORM or parameterized queries. Do not use raw SQL string concatenation (for example, `connection.execute(f"SELECT * FROM ... WHERE id = {user_input}")`).
- [ ] **Cross-Site Request Forgery (CSRF)**: Confirm that all `POST`, `PUT`, `PATCH`, and `DELETE` requests include a valid CSRF token. The system must reject any requests missing the token with an HTTP 403 Forbidden status.
- [ ] **Cross-Site Scripting (XSS)**: Ensure all user input rendered in templates is properly escaped. Avoid using Django's template `safe` filter or React's `dangerouslySetInnerHTML` unless inputs have been strictly sanitized with a trusted library like DOMPurify.

---

## 4. File Upload Hardening (Resume Storage Guard)
- [ ] **File Size Restrictions**: Reject resume uploads that exceed `5MB` directly at the application gateway.
- [ ] **Document Schema Audits**: Verify file extensions are strictly limited to `.pdf` and `.docx`.
- [ ] **Malware & Execution Protection**: Check that uploaded files are analyzed via integrated antivirus toolkits (such as ClamAV) before being committed to persistent cloud storage. Skip execution privileges entirely inside target media directories (`chmod 644`).
