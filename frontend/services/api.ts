/**
 * API client for the FastAPI backend. Kept as plain fetch wrappers
 * (no heavier data-fetching library) — appropriate for a demo's scope.
 */
import type {
  Client,
  CurrentUser,
  DashboardSummary,
  FormOut,
  OnboardingInstance,
  PortalStatus,
  Template,
} from "@/types/api";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

const TOKEN_KEY = "onboarding_os_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  window.localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  auth: boolean = true
): Promise<T> {
  const headers = new Headers(options.headers);
  if (auth) {
    const token = getToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);
  }
  if (options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      // ignore — use statusText
    }
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

// --- Auth ---
export const authApi = {
  register: (data: { organization_name: string; full_name: string; email: string; password: string }) =>
    request<{ access_token: string }>("/auth/register", { method: "POST", body: JSON.stringify(data) }, false),
  login: (data: { email: string; password: string }) =>
    request<{ access_token: string }>("/auth/login", { method: "POST", body: JSON.stringify(data) }, false),
  me: () => request<CurrentUser>("/auth/me"),
};

// --- Clients ---
export const clientsApi = {
  list: () => request<Client[]>("/clients"),
  get: (id: string) => request<Client>(`/clients/${id}`),
  create: (data: { name: string; contact: { name: string; email: string; is_primary: boolean } }) =>
    request<Client>("/clients", { method: "POST", body: JSON.stringify(data) }),
};

// --- Forms ---
export const formsApi = {
  list: () => request<FormOut[]>("/forms"),
  create: (data: { name: string; definition: { fields: unknown[] } }) =>
    request<FormOut>("/forms", { method: "POST", body: JSON.stringify(data) }),
};

// --- Templates ---
export const templatesApi = {
  list: () => request<Template[]>("/templates"),
  create: (data: { name: string; form_id: string | null; required_documents: string[] }) =>
    request<Template>("/templates", { method: "POST", body: JSON.stringify(data) }),
};

// --- Onboarding instances (staff) ---
export const instancesApi = {
  list: () => request<OnboardingInstance[]>("/onboarding-instances"),
  get: (id: string) => request<OnboardingInstance>(`/onboarding-instances/${id}`),
  create: (data: { client_id: string; template_id: string }) =>
    request<OnboardingInstance>("/onboarding-instances", { method: "POST", body: JSON.stringify(data) }),
  portalLink: (id: string) => request<{ portal_path: string }>(`/onboarding-instances/${id}/portal-link`),
  workflowStatus: (id: string) =>
    request<{ queryable: boolean; live_status?: unknown; detail?: string }>(
      `/onboarding-instances/${id}/workflow-status`
    ),
};

// --- Dashboard ---
export const dashboardApi = {
  summary: () => request<DashboardSummary>("/dashboard/summary"),
};

// --- Portal (token-based, no staff auth) ---
export const portalApi = {
  status: (token: string) => request<PortalStatus>(`/portal/${token}`, {}, false),
  submitIntake: (token: string, answers: Record<string, unknown>) =>
    request<void>(`/portal/${token}/intake`, { method: "POST", body: JSON.stringify({ answers }) }, false),
  uploadDocument: (token: string, requestId: string, file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return request<{ document_id: string; status: string }>(
      `/portal/${token}/documents/${requestId}/upload`,
      { method: "POST", body: formData },
      false
    );
  },
  connectOAuth: (token: string, provider: "GOOGLE" | "META") =>
    request<{ provider: string; status: string }>(
      `/portal/${token}/oauth/connect`,
      { method: "POST", body: JSON.stringify({ provider }) },
      false
    ),
};
