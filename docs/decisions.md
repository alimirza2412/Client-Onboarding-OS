# Architecture Decisions Log

Decisions made where the original architecture/roadmap left an
implementation detail open. All decisions below are final unless a new
entry explicitly supersedes one.

---

## 1. Workflow definition: code-defined Temporal workflows (no visual builder)

**Decision:** Onboarding workflows are implemented directly as Temporal
workflow code (Python). There is no admin-editable visual workflow builder
(no node/edge graph interpreted at runtime) for the MVP.

**Reason:** The architecture lists `workflow_nodes` / `workflow_edges` as
core entities, which usually implies a visual, drag-and-drop workflow
builder. Building a generic engine that reads a graph from the database and
executes it at runtime would mean building a custom workflow engine on top
of Temporal — which directly contradicts the project rule "do not build
custom durable workflow infrastructure; use Temporal." It also solves a
problem (non-developers redesigning flows) that doesn't exist yet with a
single vertical (Agency).

**Consequence:**
- `workflow_nodes` and `workflow_edges` tables are **not created** for MVP.
- `workflows`, `workflow_versions`, `workflow_executions`, `workflow_tasks`,
  and `workflow_approvals` are kept, used as records of what ran (for
  audit/dashboard purposes), not as an execution graph.
- If a visual builder is needed later (e.g. once multiple verticals want
  self-service flow customization), it will be scoped as its own dedicated
  future phase, built on top of the stable core engine — not retrofitted
  into Phase 7.

---

## 2. Tenant isolation: PostgreSQL Row-Level Security + application-level filtering

**Decision:** Tenant isolation is enforced in two layers:
1. Every tenant-owned table has an `organization_id` column, and every
   application query filters on it.
2. PostgreSQL Row-Level Security (RLS) policies enforce isolation at the
   database level, using a session variable (e.g. `app.current_org_id`) set
   per request.

**Reason:** Application-level filtering alone depends on every developer
remembering to add the filter in every query, forever — a single missed
`WHERE` clause leaks data across tenants. This is one of the most common
real-world SaaS data leak causes. RLS is cheap to add now, while the Phase 1
schema is first being written, and expensive to retrofit later once queries
already exist without it.

**Consequence:**
- Phase 1, Step 1.3 implementation includes RLS policy setup on every
  tenant-owned table, in addition to `organization_id` columns and
  application-level filters.
- Phase 1 testing includes a case that attempts a raw query with **no**
  application-level filter, to confirm RLS alone blocks cross-tenant access
  — not only testing through the API layer.

---

## 3. Template versioning is retained

**Decision:** Form/template versioning (`form_versions`,
`onboarding_templates` → `onboarding_instances` referencing a fixed
template state) is kept exactly as specified in the original architecture.
Submissions and instances always pin to the version that existed when they
were created, so future edits never break in-progress onboardings.

**Reason:** Explicitly required by the architecture and Phase 4's critical
test (a client on Form Version 1 must not be affected when Version 2 is
published). No change from the original design.
