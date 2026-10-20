"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, authApi, setToken } from "@/services/api";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [orgName, setOrgName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const result =
        mode === "login"
          ? await authApi.login({ email, password })
          : await authApi.register({ organization_name: orgName, full_name: fullName, email, password });
      setToken(result.access_token);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="flex flex-1 items-center justify-center p-8">
      <div className="w-full max-w-sm">
        <h1 className="text-2xl font-semibold mb-1">
          {mode === "login" ? "Log in" : "Set up your agency"}
        </h1>
        <p className="text-sm text-muted-foreground mb-6">
          {mode === "login"
            ? "Client Onboarding OS staff login."
            : "Registering creates a new organization with you as the owner."}
        </p>

        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          {mode === "register" && (
            <>
              <input
                className="rounded-md border border-input px-3 py-2 text-sm bg-transparent"
                placeholder="Agency name"
                value={orgName}
                onChange={(e) => setOrgName(e.target.value)}
                required
              />
              <input
                className="rounded-md border border-input px-3 py-2 text-sm bg-transparent"
                placeholder="Your full name"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                required
              />
            </>
          )}
          <input
            className="rounded-md border border-input px-3 py-2 text-sm bg-transparent"
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <input
            className="rounded-md border border-input px-3 py-2 text-sm bg-transparent"
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
          />

          {error && <p className="text-sm text-destructive">{error}</p>}

          <button
            type="submit"
            disabled={busy}
            className="rounded-md bg-primary text-primary-foreground px-3 py-2 text-sm font-medium disabled:opacity-50"
          >
            {busy ? "Please wait…" : mode === "login" ? "Log in" : "Create agency"}
          </button>
        </form>

        <button
          className="mt-4 text-sm underline underline-offset-4 text-muted-foreground"
          onClick={() => setMode(mode === "login" ? "register" : "login")}
        >
          {mode === "login" ? "New agency? Register instead" : "Already have an account? Log in"}
        </button>
      </div>
    </main>
  );
}
