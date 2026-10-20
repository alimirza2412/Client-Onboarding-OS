# CHANGELOG

## Demo build — Phases 1 through 13 (2-day demo/prototype)

Built on top of the approved Phase 0 foundation, following
`docs/architecture.md`, `docs/roadmap.md`, `docs/research.md`, and the
decisions in `docs/decisions.md` (B1: code-defined Temporal workflows;
D2: PostgreSQL RLS + application-level tenant filtering). Phase 14
(production deployment) is explicitly out of scope — this is a demo, not
an MVP.

Every item below was actually run and verified against a real local
Postgres and a real local Temporal server during this build — see
`DEMO_SETUP.md` § 6–11 for how to reproduce that verification yourself.

---

### Phase 1 — Database + Multi-Tenancy

- 16 tables via SQLAlchemy models + Alembic (`organizations`, `users`,
  `organization_members`, `clients`, `contacts`, `onboarding_templates`,
  `onboarding_instances`, `forms`, `form_versions`, `form_submissions`,
  `document_requests`, `documents`, `integration_accounts`,
  `workflow_executions`, `audit_logs`, `email_log`).
- Every tenant-owned table has `organization_id` (app-level filtering).
- **PostgreSQL Row-Level Security enabled on all 14 tenant tables**, with
  a policy checking `organization_id = current_setting('app.current_org_id')`.
  The app connects as a non-owner role (`onboarding_app`) specifically so
  RLS actually applies (table owners bypass RLS in Postgres by default).
- Verified for real: a raw SQL query with **zero application-level
  filter** was run as one org's session and correctly returned only that
  org's rows — proving RLS works independently of app code, not just in
  theory.
- Two `SECURITY DEFINER` functions solve the "bootstrap tenant context
  from an opaque credential" problem correctly (rather than disabling
  RLS anywhere): `resolve_portal_token` (client portal access) and
  `list_user_memberships` (resolving which org a logged-in user belongs
  to). Both are documented in their migration files.

### Phase 2 — Authentication + RBAC

- JWT-based auth: register (creates a new organization + OWNER user),
  login, `/auth/me`.
- Roles: OWNER, ADMIN, STAFF, CLIENT, enforced server-side via FastAPI
  dependencies (`require_owner`, `require_admin_or_above`,
  `require_staff_or_above`).
- Verified via the full Phase 2 test matrix: CLIENT blocked from
  admin/staff endpoints, STAFF can manage clients but not forms, ADMIN
  can manage forms, OWNER has full access — all as real pytest tests
  hitting the real API.

### Phase 3 — Client Management

- `clients` / `contacts` CRUD, client status enum
  (LEAD/ONBOARDING/ACTIVE/COMPLETED/ARCHIVED).
- Frontend: client list, create, detail pages.

### Phase 4 — Dynamic Intake Forms

- Versioned forms: `forms` → `form_versions` (immutable once published)
  → `form_submissions` (pins to a specific `form_version_id`).
- Field types: text, number, email, phone, select, checkbox, date,
  long_text. Simple conditional logic (`show_if: {field, equals}`).
- **Verified the Phase 4 critical test as a pytest**: publishing a new
  form version does not change what an existing submission references.
- Admin UI: simple field builder (add/remove fields, pick type).

### Phase 5 — Client Portal

- Real-time-feeling portal (polls every 4s) driven entirely by the
  backend: intake form rendering (respecting conditional logic),
  document upload, mocked OAuth connect buttons, live status.
- Access via a per-instance opaque token rather than a full parallel
  client-login system (see "Simplifications" below).

### Phase 6 — Document Management

- Document requests with status (REQUESTED/UPLOADED/PROCESSING/VERIFIED/
  REJECTED), file upload via the portal, stored on local disk (not
  S3/MinIO — see "Simplifications").

### Phase 7 — Temporal Workflow Engine

- **Real Temporal server + real `temporalio` Python SDK worker** —
  `OnboardingWorkflow` is a genuine code-defined workflow (decision B1),
  with signals (`submit_intake_form`, `upload_document`,
  `connect_oauth`), a query (`status`), human wait states via
  `workflow.wait_condition`, and a demo-shortened reminder timer race
  (90s, standing in for the real 24h/48h/72h cadence).
- Activities do all I/O (DB writes, mock email, AI calls) — the workflow
  function itself stays deterministic.
- **Verified the Phase 7 critical test for real**: killed the worker
  process with `kill -9` mid-workflow, confirmed it became unreachable,
  restarted it, and confirmed it resumed with signaled state intact and
  completed successfully afterward. See `DEMO_SETUP.md` § 10.
- Also verified the reminder → `BLOCKED` status → recovery path fires
  for real (a genuine email_log row, not simulated). See § 11.

### Phase 8 — Email + Notifications

- `EmailProvider` abstraction with a console/log implementation
  (`email_log` table + stdout) — no real SMTP/Resend/Postmark
  integration (see "Simplifications"). Templates: welcome, reminder,
  onboarding complete.

### Phase 9 — Agency OAuth Integrations

- `IntegrationProvider` abstraction, mocked: clicking "Connect" in the
  portal immediately marks the account CONNECTED and signals the
  workflow — no real Google/Meta OAuth redirect (see
  "Simplifications" — this needs real registered OAuth apps that don't
  exist for a demo).

### Phase 10 — AI Document Processing

- Async pipeline (as a Temporal activity): reads uploaded file text,
  calls Groq's chat completions API directly over HTTP if
  `GROQ_API_KEY` is set, otherwise falls back to a **deterministic mock
  extraction** (seeded by document content) so the demo works fully
  without any API key.
- Confidence-gated review: results below 0.75 confidence are flagged
  `NEEDS_REVIEW` rather than silently auto-approved — verified both
  paths actually occur across a run (mock confidence is randomized in
  range so both outcomes are exercised).
- AI-generated kickoff brief, same mock-fallback pattern.

### Phase 11 — Admin Dashboard

- `/dashboard/summary`: active/blocked/completed counts,
  average time-to-start (hours, computed from real
  `started_at`/`completed_at` timestamps), recent instance list.

### Phase 12 — End-to-End Agency Workflow

- All of the above connected and run start-to-finish for real via
  `backend/scripts/seed_demo.py`, which drives the entire flow through
  real HTTP calls (not internal function calls) — the same way the
  frontend does.

### Phase 13 — Testing + Security

- 15 pytest tests: health, auth, tenant isolation (Phase 1's critical
  test via the real API), full RBAC matrix, form versioning (Phase 4's
  critical test), AI mock service unit tests.
- Security practices actually implemented: RLS (not just app filtering),
  bcrypt password hashing, JWT expiry, `SECURITY DEFINER` functions
  scoped narrowly rather than disabling RLS.

### Phase 14 — Production Deployment

**Not implemented — explicitly out of scope for a demo** (Docker,
managed hosting, monitoring, backups, secrets management, etc.). See
`docs/roadmap.md` Phase 14 for what a production build would still need.

---

## Post-launch addition — AI Intake Analysis + Missing Information Detection

Added on top of the working demo above, per a follow-up audit. New:

- **AI Intake Analysis** (`app/services/ai.py:analyze_intake`) — dedicated
  Groq prompt (separate from document extraction), Pydantic-validated,
  with a deterministic mock fallback. Stored on
  `OnboardingInstance.ai_intake_analysis` (new column, additive
  migration `189e40036eb6`).
- **Missing Information Detection** (`app/services/missing_info.py`) —
  deterministic, schema-aware comparison of required form fields +
  required documents against actual submission state. No AI involved.
  Live-recomputed on read (staff + portal endpoints) rather than trusting
  the stored point-in-time snapshot, so it never looks stale as documents
  get uploaded later.
- Integrated into the existing Temporal workflow as one new activity
  (`analyze_intake_and_detect_missing`), inserted at exactly one point —
  right after intake submission, before document collection. No existing
  signals/waits/reminders were changed.
- Staff instance page: "AI Intake Summary" + "Missing Information"
  sections (formatted, not raw JSON). Client portal: progress bar +
  actionable missing items + next-action text — no AI analysis or
  internal detail exposed to the client.
- 10 new tests (`tests/test_ai_intake_analysis.py`) covering the mock
  fallback, invalid/malformed Groq output, network failures, and a full
  real-workflow integration test.

These are deliberate scope reductions for a 2-day demo, not oversights.
Each is called out in the relevant code's docstring too.

| Area | Full architecture | Demo implementation |
|---|---|---|
| Redis | Cache / temporary operations layer | Not used — nothing in the demo's scope needs a cache yet (JWT auth needs no server-side session store); omitted rather than added speculatively |
| RBAC | Dynamic `roles`/`permissions` tables | Fixed `MemberRole` enum (OWNER/ADMIN/STAFF/CLIENT) checked in code |
| Client portal auth | Full parallel client login system | Opaque per-instance access token (magic-link style) |
| File storage | S3-compatible object storage (MinIO) | Local disk (`backend/uploads/`) |
| Email | Resend/Postmark provider | Console/log provider writing to `email_log` |
| OAuth | Real Google/Meta OAuth + API verification | Mocked connect (no real credentials exist for a demo) |
| Form fields/answers | Separate `form_fields`/`form_answers` tables | JSON `definition`/`answers` columns on `form_versions`/`form_submissions` |
| Document versions | Separate `documents` + `document_versions` tables | Single `documents` row per upload |
| `workflow_nodes`/`workflow_edges` | Visual workflow graph (already excluded — decision B1) | Not created; `workflow_executions` used as an audit record only |
| Reminder cadence | 24h / 48h / 72h escalation | 90-second demo timer (configurable in `OnboardingWorkflowInput`) |
| Test database | Isolated test DB with transactional rollback per test | Tests run against the real local Postgres, using randomized emails/names to avoid collisions |
| Payments, e-signature, appointments, messages, tasks/notifications tables | Present in full schema | Not built — roadmap marks these "[later]"/beyond initial MVP already |

---

## Known issues / things to be aware of

- **No headless browser testing was possible in the build environment**
  used to create this — the backend was verified extremely thoroughly
  (real Postgres, real RLS, real Temporal, real crash/restart, 15
  passing tests, full E2E script), and the frontend passes TypeScript
  compilation, ESLint, and a production build with all pages rendering
  the correct HTTP status — but a manual click-through in an actual
  browser is recommended as a final check before a live demo.
- `.env` secrets (SECRET_KEY, DB passwords) have demo-only defaults —
  fine for local demo use, must be changed before any real deployment.
- The dashboard's "blocked" count only reflects instances currently
  waiting past the demo reminder timer for the *intake form* step
  specifically — the pattern is only wired up for that one wait state as
  a representative example, not duplicated across every wait state (see
  `app/workflows/onboarding.py`).
- `db.refresh()`-after-`commit()` patterns required a non-obvious fix
  (SQLAlchemy `after_begin` event listener) to keep the RLS session
  variable applied across multiple transactions within one request — see
  `app/database/session.py` if extending this pattern to new code.
- No rate limiting, no audit-log UI (the `audit_logs` table exists but
  nothing writes to it yet — flagged here rather than silently
  incomplete).
