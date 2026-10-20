# Client Intake / Onboarding Automation OS — Implementation Roadmap

**Important:**
- Do not unnecessarily change the approved architecture.
- Do not write code ahead of the current phase.
- The roadmap must be followed sequentially.
- Each phase must be completed and tested before moving to the next phase.

## Phase 0 — Project Foundation

- **0.1** Create repository structure: `frontend/`, `backend/`,
  `infrastructure/`, `docs/`, `tests/`.
- **0.2** Initialize FastAPI backend (FastAPI, Pydantic, SQLAlchemy,
  Alembic, configuration management). Expected: running FastAPI app with a
  health endpoint.
- **0.3** Initialize Next.js frontend (Next.js, TypeScript, Tailwind,
  shadcn/ui). Expected: frontend runs independently and can talk to the
  backend.
- **Completion:** Both frontend and backend run successfully.

## Phase 1 — Database + Multi-Tenancy

- **1.1** Set up PostgreSQL.
- **1.2** Create `organizations`, `users`, `organization_members`, `roles`,
  `permissions`.
- **1.3** Implement tenant isolation. Every tenant-owned entity must
  contain `organization_id`. *(See `docs/decisions.md`: RLS + app-level
  filtering, both layers.)*
- **Testing:** Organization A must never access Organization B data.
- **Completion:** Migrations work and cross-tenant access tests pass.

## Phase 2 — Authentication + RBAC

- **2.1** Registration, login, logout, session/token handling, password
  reset.
- **2.2** Roles: OWNER, ADMIN, STAFF, CLIENT.
- **2.3** Server-side permissions.
- **Testing:** CLIENT cannot access admin functions; STAFF cannot modify
  org settings; ADMIN can manage clients; OWNER has full org permissions.
- **Completion:** Auth and authorization enforced by backend.

## Phase 3 — Client Management

- **3.1** Create `clients`, `contacts`, `engagements`.
- **3.2** Client CRUD.
- **3.3** Client status: LEAD, ONBOARDING, ACTIVE, COMPLETED, ARCHIVED.
- Frontend: client list, client detail, create client, edit client.
- **Completion:** Client management works with permissions and tenant
  isolation.

## Phase 4 — Dynamic Intake Forms

- **4.1** Create `forms`, `form_versions`, `form_fields`,
  `form_submissions`, `form_answers`.
- **4.2** Form builder. Field types: text, number, email, phone, select,
  multi-select, checkbox, date, file, long text.
- **4.3** Conditional logic (e.g. Service = Paid Ads → show Meta Ads
  questions).
- **4.4** Immutable form versions.
- **4.5** Form submission.
- **Critical test:** Client starts Form Version 1. Admin publishes Version
  2. Existing client remains on Version 1; new client receives Version 2.
- **Completion:** Existing onboarding cannot be broken by future form
  edits.

## Phase 5 — Client Portal

- **5.1** Client authentication.
- **5.2** Onboarding portal: progress, completed actions, pending actions,
  next action.
- **5.3** Client action system: complete form, upload document, connect
  integration, schedule meeting.
- **Testing:** Client can only access their own onboarding.
- **Completion:** A client can independently navigate their onboarding.

## Phase 6 — Document Management

- **6.1** Set up S3-compatible storage / MinIO locally.
- **6.2** Document requests. Statuses: REQUESTED, UPLOADED, PROCESSING,
  VERIFIED, REJECTED.
- **6.3** Secure file upload.
- **Testing:** invalid files, large files, unauthorized files, cross-tenant
  access.
- **Completion:** Documents can be requested, uploaded, stored and tracked
  securely.

## Phase 7 — Temporal Workflow Engine

Only begin after basic domain objects are stable.

- **7.1** Set up Temporal.
- **7.2** Connect FastAPI to Temporal.
- **7.3** First onboarding workflow (e.g. OnboardingCreated → Send Welcome
  → Wait → Complete).
- **7.4** Activities: SendEmail, CreateTask, RequestDocument, UpdateStatus,
  NotifyTeam.
- **7.5** Human wait states.
- **7.6** Retries and failure recovery.
- **Critical test:** Stop/restart worker during a workflow — it must resume
  without losing state.
- **Completion:** Long-running workflows, retries and wait states work
  reliably.

> See `docs/decisions.md`: workflows are code-defined Temporal workflows,
> not an admin-editable visual graph, for MVP.

## Phase 8 — Email + Notifications

- **8.1** `EmailProvider` abstraction.
- **8.2** Templates: welcome, intake reminder, document reminder,
  onboarding complete, kickoff reminder.
- **8.3** Automated reminders (e.g. incomplete → 24h reminder → 48h
  reminder → 72h internal escalation).
- **Completion:** Temporal controls reminder timing; failed email
  operations are recoverable.

## Phase 9 — Agency OAuth Integrations

- **9.1** `IntegrationProvider` abstraction.
- **9.2** OAuth lifecycle.
- **9.3** Initial integrations, in priority order: Google, Meta, Google
  Ads, Google Analytics.
- **9.4** API connection verification. OAuth success alone is not
  considered complete:
  `OAuth → Token stored securely → API test → Permission verification →
  CONNECTED / ACTION REQUIRED`.
- **Completion:** Client can connect an external account without manually
  sharing credentials.

## Phase 10 — AI Document Processing

- **10.1** Asynchronous document-processing pipeline.
- **10.2** OCR/document parser.
- **10.3** Send clean extracted text to Groq.
- **10.4** Validate Groq output with Pydantic schemas.
- **10.5** Confidence scoring; low confidence → human review.
- **10.6** Generate AI onboarding summary (client overview, goals,
  requirements, stakeholders, missing information, potential issues, next
  steps).
- **Completion:** AI extraction is asynchronous, validated,
  confidence-aware, and never silently overrides critical data.

## Phase 11 — Admin Dashboard

Active/completed/blocked/overdue onboarding counts, onboarding progress,
missing information, next action, responsible person, time-to-start.

- **Completion:** Operations team can understand every active onboarding
  from one dashboard.

## Phase 12 — End-to-End Agency Workflow

Connect all modules:

```
Create Client
→ Start Onboarding
→ Load Template
→ Welcome Email
→ Client Portal
→ Intake
→ Documents
→ AI Processing
→ OAuth Connections
→ API Verification
→ Schedule Kickoff
→ Team Assignment
→ AI Kickoff Brief
→ Completion
```

- **Completion:** A complete Agency onboarding can be executed start to
  finish.

## Phase 13 — Testing + Security

- **Unit tests:** services, validators, permissions, workflow activities,
  AI parsing.
- **Integration tests:** API + PostgreSQL, API + Temporal, API + Storage,
  OAuth callbacks, webhook processing.
- **End-to-end:** Create Client → Complete onboarding → Verify completion.
- **Security:** tenant isolation, RBAC bypass, unauthorized files, OAuth
  security, webhook spoofing, malicious uploads, rate limiting.
- **Completion:** Critical security and end-to-end tests pass.

## Phase 14 — Production Deployment

Only after the MVP is stable.

Production components: Next.js, FastAPI, PostgreSQL, Temporal, Redis,
Object Storage, Workers, Groq, Integrations.

Add: HTTPS, backups, monitoring, logging, secrets management, health
checks, database migration strategy, error tracking, rate limiting.

- **Completion:** System can be deployed and operated reliably in
  production.

## Important Development Rules

1. Do not jump between phases.
2. Do not add unnecessary technologies.
3. Do not build all four verticals initially.
4. Build Agency first.
5. Do not build Stripe/DocuSign/WhatsApp/SMS production integrations
   during the first MVP.
6. Use mocks/development providers where appropriate.
7. Do not build custom durable workflow infrastructure; use Temporal.
8. Do not let AI directly control critical workflow state.
9. Do not allow form changes to affect existing submissions.
10. Every phase must have tests and explicit completion criteria before
    proceeding.
