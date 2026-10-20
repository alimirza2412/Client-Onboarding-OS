"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { ApiError, portalApi } from "@/services/api";
import type { FormField, PortalStatus } from "@/types/api";

function shouldShowField(field: FormField, answers: Record<string, unknown>): boolean {
  if (!field.show_if) return true;
  return answers[field.show_if.field] === field.show_if.equals;
}

function IntakeForm({ token, form, onSubmitted }: { token: string; form: { fields: FormField[] }; onSubmitted: () => void }) {
  const [answers, setAnswers] = useState<Record<string, unknown>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await portalApi.submitIntake(token, answers);
      onSubmitted();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to submit");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      {form.fields.filter((f) => shouldShowField(f, answers)).map((field) => (
        <div key={field.key} className="flex flex-col gap-1">
          <label className="text-sm font-medium">
            {field.label} {field.required && <span className="text-destructive">*</span>}
          </label>
          {field.type === "select" ? (
            <select
              className="rounded-md border border-input px-3 py-2 text-sm bg-transparent"
              required={field.required}
              value={(answers[field.key] as string) ?? ""}
              onChange={(e) => setAnswers({ ...answers, [field.key]: e.target.value })}
            >
              <option value="" disabled>
                Select…
              </option>
              {field.options?.map((opt) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}
            </select>
          ) : field.type === "long_text" ? (
            <textarea
              className="rounded-md border border-input px-3 py-2 text-sm bg-transparent"
              required={field.required}
              value={(answers[field.key] as string) ?? ""}
              onChange={(e) => setAnswers({ ...answers, [field.key]: e.target.value })}
            />
          ) : field.type === "checkbox" ? (
            <input
              type="checkbox"
              checked={Boolean(answers[field.key])}
              onChange={(e) => setAnswers({ ...answers, [field.key]: e.target.checked })}
            />
          ) : (
            <input
              type={field.type === "number" ? "number" : field.type === "email" ? "email" : field.type === "date" ? "date" : "text"}
              className="rounded-md border border-input px-3 py-2 text-sm bg-transparent"
              required={field.required}
              value={(answers[field.key] as string) ?? ""}
              onChange={(e) =>
                setAnswers({
                  ...answers,
                  [field.key]: field.type === "number" ? Number(e.target.value) : e.target.value,
                })
              }
            />
          )}
        </div>
      ))}

      {error && <p className="text-sm text-destructive">{error}</p>}

      <button
        type="submit"
        disabled={busy}
        className="rounded-md bg-primary text-primary-foreground px-4 py-2 text-sm font-medium disabled:opacity-50 self-start"
      >
        {busy ? "Submitting…" : "Submit"}
      </button>
    </form>
  );
}

function DocumentUpload({ token, requestId, requestName, uploaded }: { token: string; requestId: string; requestName: string; uploaded: boolean }) {
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(uploaded);
  const [error, setError] = useState<string | null>(null);

  async function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      await portalApi.uploadDocument(token, requestId, file);
      setDone(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex items-center justify-between rounded-md border border-border p-3">
      <span className="text-sm">{requestName}</span>
      {done ? (
        <span className="text-sm text-green-600">Uploaded ✓</span>
      ) : (
        <label className="text-sm underline underline-offset-4 cursor-pointer text-muted-foreground">
          {busy ? "Uploading…" : "Upload file"}
          <input type="file" className="hidden" onChange={handleFile} disabled={busy} />
        </label>
      )}
      {error && <span className="text-xs text-destructive ml-2">{error}</span>}
    </div>
  );
}

function OAuthConnect({ token, provider, connected, onConnected }: { token: string; provider: "GOOGLE" | "META"; connected: boolean; onConnected: () => void }) {
  const [busy, setBusy] = useState(false);

  async function handleConnect() {
    setBusy(true);
    try {
      await portalApi.connectOAuth(token, provider);
      onConnected();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex items-center justify-between rounded-md border border-border p-3">
      <span className="text-sm">{provider === "GOOGLE" ? "Google Ads / Analytics" : "Meta (Facebook/Instagram)"}</span>
      {connected ? (
        <span className="text-sm text-green-600">Connected ✓</span>
      ) : (
        <button
          onClick={handleConnect}
          disabled={busy}
          className="text-sm underline underline-offset-4 text-muted-foreground disabled:opacity-50"
        >
          {busy ? "Connecting…" : `Connect ${provider}`}
        </button>
      )}
    </div>
  );
}

export default function PortalPage() {
  const { token } = useParams<{ token: string }>();
  const [status, setStatus] = useState<PortalStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    portalApi
      .status(token)
      .then(setStatus)
      .catch((err) => setError(err instanceof ApiError ? err.message : "This portal link is invalid"));
  }, [token]);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 4000);
    return () => clearInterval(interval);
  }, [refresh]);

  if (error) {
    return (
      <main className="flex flex-1 items-center justify-center p-8">
        <p className="text-sm text-destructive">{error}</p>
      </main>
    );
  }

  if (!status) return null;

  const connectedProviders = new Set(
    status.integration_accounts.filter((a) => a.status === "CONNECTED").map((a) => a.provider)
  );

  return (
    <main className="flex-1 mx-auto w-full max-w-xl px-6 py-10">
      <h1 className="text-2xl font-semibold mb-1">Welcome, {status.client_name}</h1>
      <p className="text-sm text-muted-foreground mb-6">
        Status: <span className="text-foreground font-medium">{status.status}</span> — {status.current_step}
      </p>

      {status.missing_info && status.status !== "COMPLETED" && (
        <section className="rounded-lg border border-border p-4 mb-8">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-sm font-medium">Onboarding Progress</h2>
            <span className="text-sm font-semibold">{status.missing_info.progress_percent}%</span>
          </div>
          <div className="h-2 rounded-full bg-secondary overflow-hidden mb-4">
            <div
              className="h-full bg-primary transition-all"
              style={{ width: `${status.missing_info.progress_percent}%` }}
            />
          </div>

          {(status.missing_info.missing_fields.length > 0 || status.missing_info.missing_documents.length > 0) && (
            <div className="mb-4">
              <h3 className="text-xs font-medium text-muted-foreground mb-2">Missing information:</h3>
              <ul className="flex flex-col gap-1 text-sm">
                {status.missing_info.missing_fields.map((f, i) => (
                  <li key={`f-${i}`} className="text-destructive">
                    ⚠ {f}
                  </li>
                ))}
                {status.missing_info.missing_documents.map((d, i) => (
                  <li key={`d-${i}`} className="text-destructive">
                    ⚠ {d}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div>
            <h3 className="text-xs font-medium text-muted-foreground mb-1">Next action:</h3>
            <p className="text-sm font-medium">{status.missing_info.next_action}</p>
          </div>
        </section>
      )}

      {status.status === "COMPLETED" ? (
        <div className="rounded-lg border border-border p-6 text-center">
          <p className="text-lg font-medium mb-1">🎉 You&apos;re all set!</p>
          <p className="text-sm text-muted-foreground">
            Your onboarding is complete
            {status.kickoff_scheduled_at &&
              ` — kickoff scheduled for ${new Date(status.kickoff_scheduled_at).toLocaleString()}`}
            .
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-8">
          {!status.intake_submitted && status.intake_form ? (
            <section>
              <h2 className="text-sm font-medium text-muted-foreground mb-3">1. Tell us about your business</h2>
              <IntakeForm token={token} form={status.intake_form} onSubmitted={refresh} />
            </section>
          ) : (
            <section className="rounded-md border border-border p-3 text-sm text-green-600">
              Intake form submitted ✓
            </section>
          )}

          {status.document_requests.length > 0 && (
            <section>
              <h2 className="text-sm font-medium text-muted-foreground mb-3">2. Upload requested documents</h2>
              <div className="flex flex-col gap-2">
                {status.document_requests.map((req) => (
                  <DocumentUpload
                    key={req.id}
                    token={token}
                    requestId={req.id}
                    requestName={req.name}
                    uploaded={req.documents.length > 0}
                  />
                ))}
              </div>
            </section>
          )}

          <section>
            <h2 className="text-sm font-medium text-muted-foreground mb-3">3. Connect your accounts</h2>
            <div className="flex flex-col gap-2">
              <OAuthConnect token={token} provider="GOOGLE" connected={connectedProviders.has("GOOGLE")} onConnected={refresh} />
              <OAuthConnect token={token} provider="META" connected={connectedProviders.has("META")} onConnected={refresh} />
            </div>
          </section>
        </div>
      )}

      <p className="text-xs text-muted-foreground mt-10">This page refreshes automatically every few seconds.</p>
    </main>
  );
}
