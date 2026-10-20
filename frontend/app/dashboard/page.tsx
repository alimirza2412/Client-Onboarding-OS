"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import { DashboardShell } from "@/components/DashboardShell";
import { dashboardApi, ApiError } from "@/services/api";
import type { DashboardSummary } from "@/types/api";

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg border border-border p-4">
      <div className="text-sm text-muted-foreground">{label}</div>
      <div className="text-2xl font-semibold mt-1">{value}</div>
    </div>
  );
}

export default function DashboardPage() {
  const { user, loading, logout } = useRequireAuth();
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (loading) return;
    dashboardApi
      .summary()
      .then(setSummary)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load dashboard"));
  }, [loading]);

  if (loading) return null;

  return (
    <DashboardShell user={user} onLogout={logout}>
      <h1 className="text-xl font-semibold mb-6">Onboarding overview</h1>

      {error && <p className="text-sm text-destructive mb-4">{error}</p>}

      {summary && (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
            <StatCard label="Active" value={summary.active_count} />
            <StatCard label="Blocked" value={summary.blocked_count} />
            <StatCard label="Completed" value={summary.completed_count} />
            <StatCard
              label="Avg. time-to-start"
              value={summary.avg_time_to_start_hours != null ? `${summary.avg_time_to_start_hours}h` : "—"}
            />
          </div>

          <h2 className="text-sm font-medium text-muted-foreground mb-3">Recent onboardings</h2>
          <div className="rounded-lg border border-border divide-y divide-border">
            {summary.instances.length === 0 && (
              <p className="p-4 text-sm text-muted-foreground">
                No onboardings yet.{" "}
                <Link href="/dashboard/clients" className="underline underline-offset-4">
                  Create a client
                </Link>{" "}
                to get started.
              </p>
            )}
            {summary.instances.map((i) => (
              <Link
                key={i.id}
                href={`/dashboard/instances/${i.id}`}
                className="flex items-center justify-between p-4 text-sm hover:bg-secondary"
              >
                <span className="font-mono text-xs text-muted-foreground">{i.id.slice(0, 8)}</span>
                <span
                  className={
                    i.status === "COMPLETED"
                      ? "text-green-600"
                      : i.status === "BLOCKED"
                        ? "text-destructive"
                        : "text-foreground"
                  }
                >
                  {i.status}
                </span>
                <span className="text-muted-foreground">{i.current_step}</span>
              </Link>
            ))}
          </div>
        </>
      )}
    </DashboardShell>
  );
}
