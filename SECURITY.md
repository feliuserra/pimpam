# PimPam Security Policy

## Our security commitment

PimPam is a platform where people trust us with their data, their conversations, and their identity. That trust is everything. Security and privacy aren't features we bolt on — they're fundamental to every design decision, every line of code, and every deployment choice we make.

This document outlines our security practices, our approach to GDPR compliance, and how to report vulnerabilities.

---

## Reporting a vulnerability

If you discover a security vulnerability in PimPam, **please do not open a public issue.** Security issues require responsible disclosure to protect our users.

### How to report

Email **security@pimpam.org** (to be established) with:

- A description of the vulnerability.
- Steps to reproduce it.
- The potential impact as you understand it.
- Any suggested fix, if you have one.

### What to expect

- **Acknowledgment within 48 hours.** We'll confirm we received your report.
- **Assessment within 7 days.** We'll evaluate the severity and begin working on a fix.
- **Transparent communication.** We'll keep you informed of our progress.
- **Credit.** Unless you prefer to remain anonymous, we'll credit you in the security advisory.
- **No legal threats.** We will never pursue legal action against security researchers acting in good faith.

### What counts as "good faith"

- You give us reasonable time to fix the issue before any public disclosure.
- You don't access, modify, or delete other users' data beyond what's necessary to demonstrate the vulnerability.
- You don't exploit the vulnerability for personal gain.
- You don't use social engineering, phishing, or denial-of-service attacks.

## Supported versions

| Version | Supported |
|---------|-----------|
| Latest  | Yes       |

As PimPam is in early development, only the latest version on the main branch receives security updates. This policy will evolve as the project matures and releases stable versions.

---

## GDPR compliance

PimPam is designed from the ground up to comply with the European Union's General Data Protection Regulation (GDPR). But we don't treat GDPR as a legal checkbox — it's a reflection of our values. These principles apply to all users, not just those in the EU.

### Data protection principles

**Lawfulness, fairness, and transparency.** We only process personal data with a clear legal basis. We explain what we collect, why, and how — in plain language, not legal jargon.

**Purpose limitation.** We collect data for specific, stated purposes. We never repurpose your data for something you didn't agree to. We will never sell your data. We will never use your data for advertising. Ever.

**Data minimization.** We collect the absolute minimum data needed to provide the service. If we don't need it, we don't collect it. Every data field in our database exists because removing it would break functionality.

**Accuracy.** Users can view and correct their personal data at any time.

**Storage limitation.** We don't keep your data longer than necessary. When you delete your account, your data is actually deleted — not "soft deleted," not "anonymized and retained for analytics." Deleted.

**Integrity and confidentiality.** We protect your data with appropriate technical and organizational security measures.

### User rights

PimPam guarantees the following rights to all users:

**Right of access.** You can request a complete copy of all personal data we hold about you, in a machine-readable format, at any time.

**Right to rectification.** You can correct any inaccurate personal data we hold about you.

**Right to erasure (right to be forgotten).** You can request that we delete all your personal data. We will comply fully and promptly, deleting data from active systems and backups within 30 days.

**Right to data portability.** You can export all your data (posts, messages, profile information, media) in standard, machine-readable formats. Your data is yours. You should be able to take it and leave at any time.

**Right to restrict processing.** You can ask us to limit how we use your data while a concern is being resolved.

**Right to object.** You can object to any processing of your personal data. Since we don't do profiling, targeted advertising, or algorithmic processing, this right is straightforward for us to honor.

**Right not to be subject to automated decision-making.** PimPam does not use automated decision-making or profiling. There are no algorithms deciding what you see, and no automated systems making decisions about your account. Human moderators make moderation decisions, with transparency and the right to appeal.

### What data we collect

PimPam collects only what's strictly necessary:

- **Account data:** Username, email address, hashed password. Email is used solely for authentication and critical account notifications (like security alerts). We never send marketing emails.
- **Profile data:** Whatever you choose to share publicly (display name, bio, avatar). All optional.
- **Content data:** Posts, comments, and messages you create. Messages are end-to-end encrypted — we cannot read them.
- **Interaction data:** Who you follow, which communities you join, karma scores. This is inherent to the platform's functionality.
- **Technical data:** Minimal server logs for security and debugging, retained for a maximum of 30 days, then permanently deleted.

### What we explicitly do NOT collect

- Location data.
- Device fingerprints.
- Browsing history.
- Contact lists.
- Biometric data.
- Usage analytics or behavioral patterns.
- Third-party tracking cookies.
- Advertising identifiers.
- Any data from other apps or services on your device.

### Data Processing Agreement

For self-hosted instances, we will provide a Data Processing Agreement (DPA) template to help operators comply with GDPR when hosting PimPam for others.

### Data Protection Officer

As the project grows, we will appoint a Data Protection Officer (DPO) and establish a formal data protection governance structure.

---

## Security architecture

### Authentication and access

- Passwords are hashed using bcrypt with a high cost factor. We never store plaintext passwords.
- Session tokens are cryptographically random, short-lived, and stored securely.
- We support (and encourage) two-factor authentication.
- Rate limiting protects against brute-force attacks on all authentication endpoints.
- Account lockout after repeated failed attempts, with notification to the account owner.

### Encryption

- **In transit:** All connections use TLS 1.3. No exceptions. HTTP is redirected to HTTPS. HSTS headers are set with a long max-age.
- **At rest:** Sensitive data is encrypted at rest using AES-256.
- **Messages:** Direct messages use end-to-end encryption. The server never has access to plaintext message content. Only the sender and recipient can read messages.

### Input validation and injection prevention

- All user input is validated and sanitized on both client and server.
- Parameterized queries prevent SQL injection.
- Content Security Policy (CSP) headers mitigate XSS attacks.
- File uploads are validated for type, size, and content. Uploaded files are scanned and stored in isolated storage with no execute permissions.

### Infrastructure security

- The application follows the principle of least privilege throughout.
- Dependencies are monitored for known vulnerabilities using automated tools.
- Security headers (X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy) are set on all responses.
- Logging captures security-relevant events without capturing personal data.

### Community and content safety

- Community moderators are elected by community members and are accountable to them.
- Moderation actions are logged and transparent. Users can appeal any moderation decision.
- Content reports are handled promptly, with clear escalation paths for severe issues.
- Illegal content (CSAM, terrorism, etc.) is reported to appropriate authorities immediately.

---

## Security development practices

### Code review

Every change to PimPam's codebase goes through code review. Security-sensitive changes require review from at least two maintainers.

### Dependency management

We keep dependencies minimal and up to date. Automated vulnerability scanning runs on every pull request and on a regular schedule against the main branch.

### Testing

Security-relevant functionality is covered by automated tests, including tests for authentication, authorization, input validation, and encryption.

### Incident response

When a security incident occurs:

1. We contain the issue immediately.
2. We assess the impact and scope.
3. We notify affected users within 72 hours (as required by GDPR Article 33).
4. We publish a transparent post-mortem, including what happened, what data was affected, what we did to fix it, and what we're doing to prevent it from happening again.

We do not minimize, hide, or delay disclosure of security incidents.

---

## For self-hosted instances

PimPam is designed to be self-hostable. If you run your own PimPam instance, you are responsible for:

- Keeping your instance updated with the latest security patches.
- Configuring TLS and other transport security.
- Managing your database security and backups.
- Complying with GDPR and other applicable privacy regulations for your users.
- Establishing your own incident response procedures.

We will provide documentation and tools to make secure self-hosting as straightforward as possible.

---

## Transparency

We will publish regular transparency reports covering:

- The number and nature of content moderation actions taken.
- Any government or law enforcement requests for user data, and how we responded.
- Security incidents and their resolution.
- Changes to our privacy practices or security architecture.

No one should have to trust us blindly. The code is open. The policies are public. The reports are transparent.

---

## Contact

- **Security vulnerabilities:** security@pimpam.org (to be established)
- **Privacy and GDPR inquiries:** privacy@pimpam.org (to be established)
- **General questions:** Open an issue or start a discussion on the repository.

---

**PimPam takes your security and privacy seriously — not because regulations require it, but because respecting people is the whole point.**
