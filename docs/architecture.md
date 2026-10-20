# Client Intake / Onboarding Automation OS — Final Architecture

**Goal:** Build a production-grade Client Intake / Onboarding Automation
System, initially targeting agencies. The architecture must later support
consulting firms, recruiting firms, and law firms without rebuilding the
core.

**Core principle:** The application owns the onboarding state. AI and
third-party integrations are supporting components.

## Architecture

**Frontend:** Next.js, TypeScript, Tailwind CSS, shadcn/ui

**Backend:** Python, FastAPI, Pydantic, SQLAlchemy, Alembic

**Database:** PostgreSQL — the primary system of record.

**Workflow:** Temporal.io — responsible for durable workflow execution,
long-running waits, retries, human approvals, webhook-driven continuation,
and workflow recovery.

**Cache / temporary operations:** Redis

**File storage:** S3-compatible object storage; MinIO for local development.

**AI:** Groq API — used for classification, extraction, summarization,
missing-information detection, email drafting, and kickoff brief
generation. AI must not directly control critical workflow state.

### Document processing

```
Upload
→ Object Storage
→ Async Processing
→ OCR / Document Parser
→ Clean Text
→ Groq
→ Structured JSON
→ Pydantic Validation
→ Confidence Score
→ Human Review if required
→ PostgreSQL
```

### Authentication / Authorization

- Authentication
- RBAC
- Multi-tenancy
- Organization-level isolation

Initial roles: OWNER, ADMIN, STAFF, CLIENT

Every tenant-owned database record must have `organization_id`.

### Core database entities

```
organizations, users, organization_members, roles, permissions

clients, contacts, engagements

onboarding_templates, onboarding_instances

forms, form_versions, form_fields, form_submissions, form_answers

documents, document_requests, document_versions

workflows, workflow_versions, workflow_nodes, workflow_edges,
workflow_executions, workflow_tasks, workflow_approvals

events

messages, email_events

oauth_connections, integration_accounts

appointments, signatures, payments

tasks, notifications

audit_logs
```

> See `docs/decisions.md` — `workflow_nodes` / `workflow_edges` are not
> created for MVP (decision: code-defined Temporal workflows, no visual
> builder).

### Form versioning

Forms are immutable once used by an active onboarding.

```
Form
├── Version 1
├── Version 2
└── Version 3
```

A submission stores `form_version_id` so changes to the form cannot break
an existing onboarding.

### Integration architecture

Use provider/adaptor interfaces rather than tightly coupling business logic
to providers: `EmailProvider`, `CalendarProvider`, `PaymentProvider`,
`SignatureProvider`, `CRMProvider`, `ProjectProvider`, `IntegrationProvider`.

Initial Agency integrations: Google OAuth, Meta OAuth, Google Ads, Google
Analytics, HubSpot where useful.

### OAuth flow

```
Client
→ Connect Account
→ Provider Authorization
→ Callback
→ Encrypt/store tokens
→ Verify API access
→ Confirm permissions
→ CONNECTED
```

Never ask clients to manually send passwords or sensitive API credentials
when delegated OAuth is available.

### Event architecture

```
External Webhook
→ Verify webhook
→ Persist raw event
→ Convert to internal event
→ Temporal workflow
→ Continue workflow
```

Example events: FormSubmitted, DocumentUploaded, OAuthConnected,
SignatureCompleted, PaymentReceived, AppointmentBooked, ContractSigned.

All webhook handlers must be idempotent.

### Main onboarding workflow

```
CRM / Manual Client Creation
→ Create Onboarding
→ Load Agency Template
→ Welcome Email
→ Client Portal
→ Dynamic Intake
→ Document Collection
→ AI Extraction
→ OAuth Connections
→ API Verification
→ E-signature [later]
→ Payment [later]
→ Schedule Kickoff
→ Assign Team
→ Generate AI Kickoff Brief
→ Create Project [later]
→ ONBOARDING COMPLETE
```

**Client portal should show:** onboarding progress, completed items,
pending items, required actions, document requests, account connections,
scheduling, next action.

**Admin dashboard should show:** active onboardings, completed onboardings,
blocked onboardings, overdue onboardings, onboarding progress, missing
information, responsible person, next action, time-to-start metrics.

### Security requirements

HTTPS, RBAC, tenant isolation, encrypted OAuth tokens, secure file access,
signed file URLs, file validation/scanning, webhook verification, rate
limiting, audit logs, backups, secret management.

### Development principle

Do not build separate systems for each industry. Build one core onboarding
engine and use industry-specific templates/configuration on top of it.

Agency is Phase 1. Consulting, Recruiting and Legal are later verticals.
