# Client Intake / Onboarding Automation OS — Business + Domain Research

**Target:** Initial vertical = Agencies. Future verticals: Consulting,
Recruiting, Law.

## Core business problem

After a client says yes, professional-service businesses often have
fragmented onboarding:

```
Deal Won → Email → Intake Form → Document Requests → Contract → Signature
→ Payment → Scheduling → Team Assignment → Project Setup
```

Problems: information is scattered; clients repeat information; documents
are missing; staff manually follow up; account credentials/access are
difficult to collect; onboarding status is unclear; handoffs are missed;
work cannot start until onboarding is complete; managers lack visibility
into what is blocking the client.

## Core product opportunity

```
CRM / Sales → Client Onboarding OS → Project Delivery
```

The system should answer: What has been completed? What is missing? Who is
responsible? What is blocking onboarding? What should happen next? How
long did it take to become delivery-ready?

**Primary KPI — Time-to-Start:** Contract/Client Accepted → Delivery Ready.
The product should reduce this time.

> Open question tracked in `docs/decisions.md`-style follow-up: the exact
> trigger event/timestamp for "Contract/Client Accepted" needs to be
> pinned down before Phase 3's schema is finalized (it isn't necessarily
> the same moment as "CRM/Manual Client Creation" in the main workflow).

## Agency research

Agency onboarding typically requires: company information, business goals,
target audience, services required, brand assets, brand guidelines,
website, social accounts, advertising accounts, analytics, CRM access,
stakeholders, communication preferences, approval contact, billing contact,
KPIs, launch date.

Major problem: manual collection of advertising and analytics credentials
is unreliable and insecure.

Better approach:
```
Client → OAuth Authorization → Delegated Permissions → Callback →
Secure Token Storage → API Verification → Connection Status
```
Do not ask clients to send passwords where OAuth is available.

Agency MVP should prioritize: dynamic intake, document collection, OAuth
account connections, automatic connection verification, reminders, client
portal, AI-generated onboarding summary, AI kickoff brief, onboarding
progress dashboard.

## Consulting research

Consulting onboarding often includes: scope, goals, stakeholders, project
requirements, data access, procurement, InfoSec, vendor risk review,
security questionnaires, SSO provisioning, internal client approvals.

The main delay may be InfoSec/vendor clearance rather than the initial
questionnaire. The workflow engine must support multi-week waits,
asynchronous approvals, client-side actions, internal approvals, security
review, SSO provisioning, retries, escalation, resume after interruption.

Consulting should be added after Agency MVP.

## Recruiting research

Recruiting onboarding needs: job title, number of openings, location,
remote/hybrid, salary, skills, experience, benefits, interview process,
hiring manager, evaluation criteria, deadline, fee structure.

Static intake forms are insufficient because initial requirements may not
produce a usable sourcing brief. Better workflow:

```
Job Intake → AI-generated Job Brief → Recruiter Review →
Initial Candidate Calibration → Client Feedback → Refined Requirements →
Second Candidate Batch → Approved Calibration → Full Sourcing
```

Recruiting should be added after the core engine is stable.

## Legal research

Legal onboarding includes: client intake, conflict checking, consultation,
engagement agreement, e-signature, retainer, document collection, matter
creation, attorney assignment, client communication.

Important constraints: conflict checks cannot rely only on simple string
matching — a stronger system requires relational/entity mapping across
clients, individuals, companies, opposing parties, related parties, and
matters. Legal matters also require strict matter-level isolation
("Ethical Walls"). Trust-account/IOLTA-related payments require
specialized legal payment workflows; a normal payment flow is not
sufficient.

Legal is a later, specialized vertical rather than the initial MVP.

## Document AI research

```
File Upload → Object Storage → Async Processing → OCR / Document Parser →
Extracted Text → Groq → Structured JSON → Schema Validation →
Confidence Score → Human Review if needed
```

Groq is the LLM layer, not the complete document-ingestion system. Scanned,
low-quality or complex documents require preprocessing/OCR/document
parsing. AI should be used for classification, extraction, summarization,
missing-information detection, drafting. AI should NOT be the source of
truth for workflow state.

## Workflow research

Simple custom database queues are insufficient for complex long-running
workflows involving multi-day/week waits, human approvals, retries,
webhooks, external API failures, workflow recovery, and asynchronous
client actions. Use Temporal as the durable workflow engine. The workflow
must survive application/worker restarts.

## Email research

Do not make Gmail/Outlook mailbox OAuth the default transactional email
architecture. Prefer a transactional email provider abstraction for
system-generated emails (e.g. Resend, Postmark). User OAuth should
primarily be used where user authorization is genuinely required, such as
calendar sync or external account connection. For development, email can
be mocked/logged.

## Cost / MVP research

Design to minimize paid services. Free/self-hosted for MVP: Next.js,
FastAPI, PostgreSQL, Redis, Temporal (self-hosted), MinIO, open-source OCR,
Groq (free tier), Google APIs (quota-based).

Potential paid production services: Stripe, DocuSign, Twilio, WhatsApp
production messaging, cloud hosting, managed database, managed Temporal,
transactional email beyond free limits.

For MVP: Payment → Mock. E-signature → Mock/Developer environment.
SMS → Mock. WhatsApp → Mock. Build provider abstractions so these can be
replaced later without changing the core onboarding engine.

## Product positioning

Do not position as: AI chatbot, form builder, Zapier alternative, generic
automation tool.

Position as: **AI-powered Client Onboarding OS.**

Core promise: "Turn a signed/accepted client into a delivery-ready client
automatically." Alternative: "The operational bridge between CRM and
project delivery."

```
HubSpot / Salesforce → Client Onboarding OS → Asana / ClickUp
```

Future: Legal → Clio. Recruiting → ATS. Consulting → Enterprise delivery
systems.

## Core differentiator

The product does not simply send automated emails — it maintains the
complete onboarding state. It knows what is complete, what is missing,
what is blocked, who needs to act, when to remind them, when to escalate,
and when onboarding is complete.

## Key architectural principles

1. PostgreSQL is the system of record.
2. Temporal owns durable workflow execution.
3. Redis handles cache/temporary operations.
4. Object storage owns files.
5. Groq provides AI capabilities.
6. FastAPI owns backend business logic.
7. Next.js owns the user experience.
8. Third-party integrations are replaceable adapters.
9. AI assists the workflow but does not own critical state.
10. Existing onboarding instances must remain stable when forms/templates
    change.
11. Every tenant must be isolated.
12. Critical actions must be auditable.
13. OAuth should replace manual credential collection wherever possible.
14. Agency is the first production vertical.
15. Consulting, Recruiting and Legal are later verticals built on the same
    core engine.
