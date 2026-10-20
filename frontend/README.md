# Frontend

Next.js (App Router) + TypeScript + Tailwind CSS + shadcn/ui.

Serves the client portal and the admin dashboard.

**Status:** Phase 0, Step 0.3 complete — app scaffolded, Tailwind and
shadcn/ui configured, placeholder routes in place. No authentication or
real functionality yet; those start in later phases.

## Structure

```
frontend/
├── app/
│   ├── layout.tsx      # Root layout
│   ├── page.tsx         # / (home) — placeholder
│   ├── login/           # /login — placeholder, real auth in Phase 2
│   ├── dashboard/        # /dashboard — placeholder, real dashboard in Phase 11
│   ├── portal/            # /portal — placeholder, real client portal in Phase 5
│   └── globals.css        # Tailwind + shadcn/ui design tokens
├── components/
│   └── ui/                 # shadcn/ui components land here (none added yet)
├── lib/
│   └── utils.ts              # shadcn/ui's `cn()` class-merging helper
├── hooks/                     # React hooks (empty — added as needed)
├── services/
│   └── api.ts                  # Thin fetch wrapper pointed at the backend
├── types/                       # Shared TypeScript types (empty — added as needed)
├── components.json               # shadcn/ui CLI config
├── .env.local.example
└── package.json
```

## Setup

Requires Node.js 20+.

```bash
cd frontend
npm install
cp .env.local.example .env.local
```

`.env.local` only needs `NEXT_PUBLIC_API_URL` — it defaults to the local
FastAPI backend (`http://127.0.0.1:8000`, see `../backend/README.md`).

## Development

```bash
npm run dev
```

Visit http://localhost:3000. Routes available: `/`, `/login`, `/dashboard`,
`/portal` (all placeholders for now).

## Build

```bash
npm run build
npm run start   # serve the production build locally
```

## Adding shadcn/ui components

The project is pre-configured (`components.json`), so once you're on a
machine with normal internet access you can add components directly:

```bash
npx shadcn@latest add button
```

> Note: `shadcn init` was not run via its CLI when this foundation was
> built, because that environment's network was restricted and couldn't
> reach `ui.shadcn.com`. The equivalent config (`components.json`,
> `lib/utils.ts`, and the CSS variables in `app/globals.css`) was set up
> by hand instead, matching what the CLI would generate. `npx shadcn add`
> should work normally from here.

## Notes

- Fonts use the system font stack, not `next/font/google` — this avoids a
  build-time dependency on Google Fonts being reachable, which caused
  production builds to fail in the sandboxed environment this was built
  in. Swap in a different font later if desired.
- No authentication or API business logic is implemented yet — `services/api.ts`
  is just a base URL + fetch wrapper.
