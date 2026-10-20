"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import { DashboardShell } from "@/components/DashboardShell";
import { clientsApi, instancesApi, templatesApi, ApiError } from "@/services/api";
import type { Client, OnboardingInstance, Template } from "@/types/api";

export default function ClientDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { user, loading, logout } = useRequireAuth();

  const [client, setClient] = useState<Client | null>(null);
  const [instances, setInstances] = useState<OnboardingInstance[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function refresh() {
    clientsApi.get(id).then(setClient).catch(() => setError("Client not found"));
    instancesApi.list().then((all) => setInstances(all.filter((i) => i.client_id === id)));
    templatesApi.list().then((t) => {
      setTemplates(t);
      if (t.length > 0) setSelectedTemplate(t[0].id);
    });
  }

  useEffect(() => {
    if (!loading) refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loading, id]);

  async function handleStartOnboarding() {
    setBusy(true);
    setError(null);
    try {
      const instance = await instancesApi.create({ client_id: id, template_id: selectedTemplate });
      router.push(`/dashboard/instances/${instance.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to start onboarding");
    } finally {
      setBusy(false);
    }
  }

  if (loading) return null;

  return (
    <DashboardShell user={user} onLogout={logout}>
      {error && <p className="text-sm text-destructive mb-4">{error}</p>}
      {client && (
        <>
          <h1 className="text-xl font-semibold mb-1">{client.name}</h1>
          <p className="text-sm text-muted-foreground mb-6">
            {client.contacts[0]?.name} · {client.contacts[0]?.email} · {client.status}
          </p>

          <div className="rounded-lg border border-border p-4 mb-8 flex items-end gap-3">
            {templates.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No onboarding templates yet.{" "}
                <Link href="/dashboard/templates" className="underline underline-offset-4">
                  Create one first
                </Link>
                .
              </p>
            ) : (
              <>
                <div className="flex flex-col gap-1">
                  <label className="text-xs text-muted-foreground">Onboarding template</label>
                  <select
                    className="rounded-md border border-input px-3 py-2 text-sm bg-transparent"
                    value={selectedTemplate}
                    onChange={(e) => setSelectedTemplate(e.target.value)}
                  >
                    {templates.map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.name}
                      </option>
                    ))}
                  </select>
                </div>
                <button
                  onClick={handleStartOnboarding}
                  disabled={busy}
                  className="rounded-md bg-primary text-primary-foreground px-3 py-2 text-sm font-medium disabled:opacity-50"
                >
                  {busy ? "Starting…" : "Start onboarding"}
                </button>
              </>
            )}
          </div>

          <h2 className="text-sm font-medium text-muted-foreground mb-3">Onboarding history</h2>
          <div className="rounded-lg border border-border divide-y divide-border">
            {instances.length === 0 && (
              <p className="p-4 text-sm text-muted-foreground">No onboardings started yet.</p>
            )}
            {instances.map((i) => (
              <Link
                key={i.id}
                href={`/dashboard/instances/${i.id}`}
                className="flex items-center justify-between p-4 text-sm hover:bg-secondary"
              >
                <span>{i.status}</span>
                <span className="text-muted-foreground">{i.current_step}</span>
              </Link>
            ))}
          </div>
        </>
      )}
    </DashboardShell>
  );
}
