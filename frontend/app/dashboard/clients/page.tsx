"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import { DashboardShell } from "@/components/DashboardShell";
import { clientsApi, ApiError } from "@/services/api";
import type { Client } from "@/types/api";

export default function ClientsPage() {
  const { user, loading, logout } = useRequireAuth();
  const [clients, setClients] = useState<Client[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  const [name, setName] = useState("");
  const [contactName, setContactName] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [busy, setBusy] = useState(false);

  function refresh() {
    clientsApi
      .list()
      .then(setClients)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load clients"));
  }

  useEffect(() => {
    if (!loading) refresh();
  }, [loading]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await clientsApi.create({
        name,
        contact: { name: contactName, email: contactEmail, is_primary: true },
      });
      setName("");
      setContactName("");
      setContactEmail("");
      setShowForm(false);
      refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create client");
    } finally {
      setBusy(false);
    }
  }

  if (loading) return null;

  return (
    <DashboardShell user={user} onLogout={logout}>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-semibold">Clients</h1>
        <button
          onClick={() => setShowForm(!showForm)}
          className="rounded-md bg-primary text-primary-foreground px-3 py-1.5 text-sm font-medium"
        >
          {showForm ? "Cancel" : "New client"}
        </button>
      </div>

      {error && <p className="text-sm text-destructive mb-4">{error}</p>}

      {showForm && (
        <form onSubmit={handleCreate} className="rounded-lg border border-border p-4 mb-6 flex flex-col gap-3 max-w-md">
          <input
            className="rounded-md border border-input px-3 py-2 text-sm bg-transparent"
            placeholder="Client / company name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
          <input
            className="rounded-md border border-input px-3 py-2 text-sm bg-transparent"
            placeholder="Primary contact name"
            value={contactName}
            onChange={(e) => setContactName(e.target.value)}
            required
          />
          <input
            className="rounded-md border border-input px-3 py-2 text-sm bg-transparent"
            type="email"
            placeholder="Primary contact email"
            value={contactEmail}
            onChange={(e) => setContactEmail(e.target.value)}
            required
          />
          <button
            type="submit"
            disabled={busy}
            className="rounded-md bg-primary text-primary-foreground px-3 py-2 text-sm font-medium disabled:opacity-50 self-start"
          >
            {busy ? "Creating…" : "Create client"}
          </button>
        </form>
      )}

      <div className="rounded-lg border border-border divide-y divide-border">
        {clients.length === 0 && <p className="p-4 text-sm text-muted-foreground">No clients yet.</p>}
        {clients.map((c) => (
          <Link
            key={c.id}
            href={`/dashboard/clients/${c.id}`}
            className="flex items-center justify-between p-4 text-sm hover:bg-secondary"
          >
            <span className="font-medium">{c.name}</span>
            <span className="text-muted-foreground">{c.contacts[0]?.email}</span>
            <span>{c.status}</span>
          </Link>
        ))}
      </div>
    </DashboardShell>
  );
}
