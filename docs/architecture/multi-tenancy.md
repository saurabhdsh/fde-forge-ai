# Multi-Tenancy Design

## Isolation layers

1. **API** — `RequestContext.organization_id` from JWT; path IDs compared to session org
2. **Service** — all mutations scoped to organization
3. **Repository** — queries include `organization_id` predicates
4. **Database** — `organization_id` columns + indexes; optional RLS prepared for later

## Tenant-owned entities (Phase 1)

Users, profiles, learner profiles, resumes, AI extractions, learner skills, sessions, refresh tokens, audit logs, organization settings.

## Shared / global entities

Permissions, system roles (`organization_id IS NULL`), competency pillars, skill levels, and the base skills taxonomy.

## Future RLS

PostgreSQL row-level security can be enabled with a session variable `app.current_org_id` set by the API connection middleware. Not enabled in Phase 1 to keep local ops simple; design is compatible.
