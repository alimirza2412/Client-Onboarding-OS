import Link from "next/link";

export default function Home() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-4 p-8 text-center">
      <h1 className="text-2xl font-semibold">Client Onboarding OS</h1>
      <p className="max-w-md text-muted-foreground">
        AI-powered onboarding for marketing agencies — turn a signed client into a delivery-ready client
        automatically.
      </p>
      <nav className="flex gap-4 text-sm underline underline-offset-4">
        <Link href="/login">Staff login</Link>
        <Link href="/dashboard">Dashboard</Link>
      </nav>
      <p className="text-xs text-muted-foreground mt-4">
        Client portal links are generated per onboarding — see the dashboard.
      </p>
    </main>
  );
}
