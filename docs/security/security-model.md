# Security Model

## Authentication

- Email/password with Argon2id
- Access JWT (short-lived) + rotating refresh tokens
- HttpOnly cookies; CSRF header required for mutating cookie auth
- Account lockout after repeated failures

## Authorization

Permission codes (e.g. `learner.self`, `audit.read`) are enforced in FastAPI dependencies. Roles are many-to-many with users; users may hold multiple roles.

## Data protection

- Secrets via environment variables only
- Passwords, tokens, and API keys are never written to audit logs or application logs
- Uploaded resume content is not logged by default
- File type and size validation on upload

## SSO extension points

Interfaces/configuration placeholders exist for Microsoft Entra ID, Google Workspace, SAML 2.0, and OIDC. These are not implemented and must not be simulated.

## Healthcare / Life Sciences

Training platform disclaimers apply. PHI-sensitive and GxP-controlled classifications are reserved for later content modules.
