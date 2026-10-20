"use client";

import { useEffect, useState } from "react";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import { DashboardShell } from "@/components/DashboardShell";
import { formsApi, ApiError } from "@/services/api";
import type { FormField, FormOut } from "@/types/api";

const FIELD_TYPES = ["text", "number", "email", "phone", "select", "checkbox", "date", "long_text"];

export default function FormsPage() {
  const { user, loading, logout } = useRequireAuth();
  const [forms, setForms] = useState<FormOut[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  const [name, setName] = useState("");
  const [fields, setFields] = useState<FormField[]>([
    { key: "company_name", label: "Company name", type: "text", required: true },
  ]);
  const [busy, setBusy] = useState(false);

  function refresh() {
    formsApi
      .list()
      .then(setForms)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load forms"));
  }

  useEffect(() => {
    if (!loading) refresh();
  }, [loading]);

  function updateField(index: number, patch: Partial<FormField>) {
    setFields(fields.map((f, i) => (i === index ? { ...f, ...patch } : f)));
  }

  function addField() {
    setFields([...fields, { key: "", label: "", type: "text", required: false }]);
  }

  function removeField(index: number) {
    setFields(fields.filter((_, i) => i !== index));
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await formsApi.create({ name, definition: { fields } });
      setName("");
      setFields([{ key: "company_name", label: "Company name", type: "text", required: true }]);
      setShowForm(false);
      refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create form");
    } finally {
      setBusy(false);
    }
  }

  if (loading) return null;

  return (
    <DashboardShell user={user} onLogout={logout}>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-semibold">Intake forms</h1>
        <button
          onClick={() => setShowForm(!showForm)}
          className="rounded-md bg-primary text-primary-foreground px-3 py-1.5 text-sm font-medium"
        >
          {showForm ? "Cancel" : "New form"}
        </button>
      </div>

      {error && <p className="text-sm text-destructive mb-4">{error}</p>}

      {showForm && (
        <form onSubmit={handleCreate} className="rounded-lg border border-border p-4 mb-6 flex flex-col gap-4 max-w-2xl">
          <input
            className="rounded-md border border-input px-3 py-2 text-sm bg-transparent"
            placeholder="Form name (e.g. Agency Intake)"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />

          <div className="flex flex-col gap-2">
            {fields.map((field, i) => (
              <div key={i} className="flex flex-wrap items-center gap-2 rounded-md border border-border p-2">
                <input
                  className="rounded-md border border-input px-2 py-1 text-xs bg-transparent w-32"
                  placeholder="key"
                  value={field.key}
                  onChange={(e) => updateField(i, { key: e.target.value })}
                  required
                />
                <input
                  className="rounded-md border border-input px-2 py-1 text-xs bg-transparent w-40"
                  placeholder="Label"
                  value={field.label}
                  onChange={(e) => updateField(i, { label: e.target.value })}
                  required
                />
                <select
                  className="rounded-md border border-input px-2 py-1 text-xs bg-transparent"
                  value={field.type}
                  onChange={(e) => updateField(i, { type: e.target.value })}
                >
                  {FIELD_TYPES.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
                <label className="flex items-center gap-1 text-xs">
                  <input
                    type="checkbox"
                    checked={field.required}
                    onChange={(e) => updateField(i, { required: e.target.checked })}
                  />
                  required
                </label>
                <button
                  type="button"
                  onClick={() => removeField(i)}
                  className="text-xs text-destructive ml-auto"
                >
                  Remove
                </button>
              </div>
            ))}
            <button
              type="button"
              onClick={addField}
              className="text-xs underline underline-offset-4 self-start text-muted-foreground"
            >
              + Add field
            </button>
          </div>

          <button
            type="submit"
            disabled={busy}
            className="rounded-md bg-primary text-primary-foreground px-3 py-2 text-sm font-medium disabled:opacity-50 self-start"
          >
            {busy ? "Creating…" : "Create form (version 1, published)"}
          </button>
        </form>
      )}

      <div className="rounded-lg border border-border divide-y divide-border">
        {forms.length === 0 && <p className="p-4 text-sm text-muted-foreground">No forms yet.</p>}
        {forms.map((f) => (
          <div key={f.id} className="p-4 text-sm">
            <div className="flex items-center justify-between">
              <span className="font-medium">{f.name}</span>
              <span className="text-muted-foreground">
                {f.versions.length} version{f.versions.length !== 1 ? "s" : ""}
              </span>
            </div>
            <div className="mt-1 text-xs text-muted-foreground">
              {f.versions[f.versions.length - 1]?.definition.fields.map((fl) => fl.label).join(", ")}
            </div>
          </div>
        ))}
      </div>
    </DashboardShell>
  );
}
