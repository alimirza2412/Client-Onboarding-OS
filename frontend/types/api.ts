export type MemberRole = "OWNER" | "ADMIN" | "STAFF" | "CLIENT";

export interface Membership {
  organization_id: string;
  organization_name: string;
  role: MemberRole;
}

export interface CurrentUser {
  id: string;
  email: string;
  full_name: string;
  memberships: Membership[];
}

export type ClientStatus = "LEAD" | "ONBOARDING" | "ACTIVE" | "COMPLETED" | "ARCHIVED";

export interface Contact {
  id: string;
  name: string;
  email: string;
  is_primary: boolean;
}

export interface Client {
  id: string;
  name: string;
  status: ClientStatus;
  created_at: string;
  contacts: Contact[];
}

export interface FormField {
  key: string;
  label: string;
  type: string;
  required: boolean;
  options?: string[] | null;
  show_if?: { field: string; equals: string } | null;
}

export interface FormVersion {
  id: string;
  version_number: number;
  definition: { fields: FormField[] };
  is_published: boolean;
  created_at: string;
}

export interface FormOut {
  id: string;
  name: string;
  created_at: string;
  versions: FormVersion[];
}

export interface Template {
  id: string;
  name: string;
  form_id: string | null;
  required_documents: string[];
  is_default: boolean;
}

export type OnboardingInstanceStatus = "NOT_STARTED" | "IN_PROGRESS" | "BLOCKED" | "COMPLETED";
export type DocumentRequestStatus = "REQUESTED" | "UPLOADED" | "PROCESSING" | "VERIFIED" | "REJECTED";
export type DocumentReviewStatus = "PENDING" | "AUTO_APPROVED" | "NEEDS_REVIEW" | "APPROVED";
export type IntegrationProvider = "GOOGLE" | "META";
export type IntegrationStatus = "NOT_CONNECTED" | "CONNECTED" | "ACTION_REQUIRED";

export interface DocumentOut {
  id: string;
  original_filename: string;
  uploaded_at: string;
  ai_extracted_data: Record<string, unknown> | null;
  ai_confidence: number | null;
  review_status: DocumentReviewStatus;
}

export interface DocumentRequestOut {
  id: string;
  name: string;
  status: DocumentRequestStatus;
  documents: DocumentOut[];
}

export interface IntegrationAccountOut {
  provider: IntegrationProvider;
  status: IntegrationStatus;
  connected_at: string | null;
}

export interface AIIntakeAnalysis {
  client_overview: string;
  goals: string[];
  requested_services: string[];
  key_requirements: string[];
  important_details: string[];
  potential_concerns: string[];
  generated_by: "groq" | "mock";
}

export interface StaffMissingInfo {
  missing_fields: string[];
  missing_documents: string[];
  completed_fields: string[];
  completed_documents: string[];
  progress_percent: number;
}

export interface PortalMissingInfo {
  progress_percent: number;
  missing_fields: string[];
  missing_documents: string[];
  next_action: string;
}

export interface OnboardingInstance {
  id: string;
  client_id: string;
  status: OnboardingInstanceStatus;
  current_step: string;
  started_at: string | null;
  completed_at: string | null;
  kickoff_scheduled_at: string | null;
  kickoff_brief: Record<string, unknown> | null;
  intake_answers: Record<string, unknown> | null;
  ai_intake_analysis: AIIntakeAnalysis | null;
  missing_info: StaffMissingInfo | null;
  document_requests: DocumentRequestOut[];
  integration_accounts: IntegrationAccountOut[];
}

export interface PortalStatus {
  id: string;
  client_name: string;
  status: OnboardingInstanceStatus;
  current_step: string;
  kickoff_scheduled_at: string | null;
  intake_submitted: boolean;
  intake_form: { fields: FormField[] } | null;
  missing_info: PortalMissingInfo | null;
  document_requests: DocumentRequestOut[];
  integration_accounts: IntegrationAccountOut[];
}

export interface DashboardSummary {
  active_count: number;
  blocked_count: number;
  completed_count: number;
  not_started_count: number;
  avg_time_to_start_hours: number | null;
  instances: {
    id: string;
    client_id: string;
    status: OnboardingInstanceStatus;
    current_step: string;
    started_at: string | null;
    completed_at: string | null;
  }[];
}
