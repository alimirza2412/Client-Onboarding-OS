"use client";

import { useEffect, useState } from "react";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import { DashboardShell } from "@/components/DashboardShell";
import { formsApi, templatesApi, ApiError } from "@/services/api";
import type { FormOut, Template } from "@/types/api";

export default function TemplatesPage() {
  const { user, loading, logout } = useRequireAuth();
  const [templates, setTemplates] = useState<Template[]>([]);
  const [forms, setForms] = useState<FormOut[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  const [name, setName] = useState("");
  const [formId, setFormId] = useState("");
  const [docsText, setDocsText] = useState("Brand Guidelines, W9 Form");
  const [busy, setBusy] = useState(false);

  function refresh() {
    templatesApi
      .list()
      .then(setTemplates)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load templates"));
    formsApi.list().then((f) => {
      setForms(f);
      if (f.length > 0) setFormId(f[0].id);
    });
  }

  useEffect(() => {
    if (!loading) refresh();
  }, [loading]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await templatesApi.create({
        name,
        form_id: formId || null,
        required_documents: docsText
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
      });
      setName("");
      setShowForm(false);
      refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create template");
    } finally {
      setBusy(false);
    }
  }

  if (loading) return null;

  return (
    <DashboardShell user={user} onLogout={logout}>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-semibold">Onboarding templates</h1>
        <button
          onClick={() => setShowForm(!showForm)}
          className="rounded-md bg-primary text-primary-foreground px-3 py-1.5 text-sm font-medium"
        >
          {showForm ? "Cancel" : "New template"}
        </button>
      </div>

      {error && <p className="text-sm text-destructive mb-4">{error}</p>}

      {showForm && (
        <form onSubmit={handleCreate} className="rounded-lg border border-border p-4 mb-6 flex flex-col gap-3 max-w-md">
          <input
            className="rounded-md border border-input px-3 py-2 text-sm bg-transparent"
            placeholder="Template name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
          <div className="flex flex-col gap-1">
            <label className="text-xs text-muted-foreground">Intake form</label>
            {forms.length === 0 ? (
              <p className="text-xs text-muted-foreground">Create a form first.</p>
            ) : (
              <select
                className="rounded-md border border-input px-3 py-2 text-sm bg-transparent"
                value={formId}
                onChange={(e) => setFormId(e.target.value)}
              >
                {forms.map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.name}
                  </option>
                ))}
              </select>
            )}
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-muted-foreground">Required documents (comma-separated)</label>
            <input
              className="rounded-md border border-input px-3 py-2 text-sm bg-transparent"
              value={docsText}
              onChange={(e) => setDocsText(e.target.value)}
            />
          </div>
          <button
            type="submit"
            disabled={busy}
            className="rounded-md bg-primary text-primary-foreground px-3 py-2 text-sm font-medium disabled:opacity-50 self-start"
          >
            {busy ? "Creating…" : "Create template"}
          </button>
        </form>
      )}

      <div className="rounded-lg border border-border divide-y divide-border">
        {templates.length === 0 && <p className="p-4 text-sm text-muted-foreground">No templates yet.</p>}
        {templates.map((t) => (
          <div key={t.id} className="p-4 text-sm">
            <div className="font-medium">{t.name}</div>
            <div className="text-xs text-muted-foreground mt-1">
              Documents: {t.required_documents.join(", ") || "none"}
            </div>
          </div>
        ))}
      </div>
    </DashboardShell>
  );
}
