"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { CurrentUser } from "@/types/api";

const NAV = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/dashboard/clients", label: "Clients" },
  { href: "/dashboard/forms", label: "Forms" },
  { href: "/dashboard/templates", label: "Templates" },
];

export function DashboardShell({
  user,
  onLogout,
  children,
}: {
  user: CurrentUser | null;
  onLogout: () => void;
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const org = user?.memberships?.[0];

  return (
    <div className="min-h-full flex flex-col">
      <header className="border-b border-border">
        <div className="mx-auto max-w-6xl px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <span className="font-semibold">Client Onboarding OS</span>
            <nav className="flex gap-4 text-sm">
              {NAV.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={
                    pathname === item.href
                      ? "font-medium underline underline-offset-4"
                      : "text-muted-foreground hover:text-foreground"
                  }
                >
                  {item.label}
                </Link>
              ))}
            </nav>
          </div>
          <div className="flex items-center gap-3 text-sm">
            {org && (
              <span className="text-muted-foreground">
                {org.organization_name} · {org.role}
              </span>
            )}
            <button
              onClick={onLogout}
              className="rounded-md border border-border px-3 py-1.5 hover:bg-secondary"
            >
              Log out
            </button>
          </div>
        </div>
      </header>
      <main className="flex-1 mx-auto w-full max-w-6xl px-6 py-8">{children}</main>
    </div>
  );
}
