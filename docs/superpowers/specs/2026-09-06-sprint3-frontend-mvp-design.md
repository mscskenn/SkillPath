# Sprint 3 — Frontend MVP design spec

## Context

Sprint 1 (data ingestion) and Sprint 2 (FastAPI backend, `POST /paths`) are
done and merged. Sprint 3 builds the Next.js frontend against the visual/UX
design already specified in `docs/superpowers/specs/DESIGN.md`, which covers
the whole app (7 screens). Per the roadmap in `CLAUDE.md`, Sprint 3 absorbs 6
of those 7 screens plus the shared visual system; the 7th (login/signup) is
deferred to Sprint 4, since it needs real auth to mean anything.

This spec covers only the architecture and integration decisions Sprint 3
needs beyond what DESIGN.md already answers (layout, spacing, color, copy).
DESIGN.md remains the source of truth for anything visual.

## Goals

- Ship a working frontend for: goal input, course browsing, path view,
  progress tracking — the four features named in the roadmap's Sprint 3 line.
- Build to DESIGN.md's screens: landing, onboarding, dashboard, search/browse,
  course detail, profile, plus the shared layout/nav and Tailwind theme.
- Wire the frontend to the real FastAPI backend (no mocked data).

## Non-goals

- Login/signup screen and real authentication — Sprint 4.
- Any new database tables for users/progress — explicitly deferred (see
  Decision 1).
- Frontend automated tests (Jest/RTL, Playwright, etc.) — skipped this
  sprint; revisit later if time allows. Backend keeps its existing pytest
  suite untouched.

## Decision 1: no-auth data model

DESIGN.md's Dashboard and Profile screens assume a saved "my path" and
persisted progress, but `users`/`user_goals`/progress tables don't exist yet
(they're explicitly later-sprint, post-auth, per `CLAUDE.md`'s schema
section). Sprint 3 has no auth.

**Decision: client-side only.** The selected goal's path (the ordered step
list returned by `POST /paths`) and step-completion state are stored in the
browser's `localStorage`, under one key (e.g. `skillpath.currentPath`). No
backend schema changes. When Sprint 4 adds real auth, this is replaced by
server-persisted progress — the localStorage shape should stay simple enough
that migrating it later is a straightforward mapping, not a rewrite.

Consequence: progress is per-browser, not per-account, until Sprint 4. This
is acceptable for an MVP demo and was chosen explicitly over standing up
throwaway anonymous-session backend tables.

## Decision 2: API integration — direct client-side fetch

The browser calls FastAPI directly (e.g. `http://localhost:8000`) rather than
proxying through Next.js API routes. Chosen over a proxy because this is a
portfolio project meant to demonstrate real pipeline/backend work — a direct
call keeps that visible rather than hidden behind a Next.js layer.

**Requires:** CORS middleware added to `backend/main.py`, allowing the
Next.js dev origin (`http://localhost:3000`). This was a deferred item from
Sprint 2 and becomes required now.

## Decision 3: routing and project structure

- New `frontend/` directory at the repo root, sibling to `backend/`.
- Next.js **App Router**, TypeScript, Tailwind CSS (per `DESIGN.md` section 8
  and `CLAUDE.md`'s tech stack).
- Routes:
  - `/onboarding` — goal input. The one route outside the shared layout, per
    DESIGN.md's "onboarding is the only strictly linear part" framing.
  - `/` — landing page for a first-time visitor with no saved goal in
    localStorage; redirects to the dashboard view once a goal/path exists.
    (Folding "landing" and "dashboard" into the same route by client-side
    state check, rather than two separate routes, avoids a redundant
    marketing route colliding with the hub DESIGN.md describes.)
  - `/browse` — search/browse screen.
  - `/course/[id]` — course detail screen.
  - `/profile` — profile/progress screen.
- Shared layout (`app/layout.tsx`) provides the persistent nav for
  `/`, `/browse`, `/course/[id]`, `/profile` — the four hub-and-spoke screens
  DESIGN.md describes as siblings, not a fixed sequence.

## Decision 4: state management

One small custom hook, `useLocalPath()`, wrapping localStorage read/write for
the current path and progress state. No Context provider, no external state
library (Redux, Zustand, etc.) — the state surface is small enough that a
hook is sufficient, and avoiding a library keeps one less new concept to
learn alongside Next.js itself.

Screens render as server components where content is static or fetched once
per load (landing, browse results); client components where interactivity is
needed (progress toggles, the onboarding form, anything reading/writing
`useLocalPath()`).

## Decision 5: backend surface gaps

`POST /paths` (Sprint 2) only serves the onboarding → dashboard flow. Two
screens in Sprint 3's scope have no backend endpoint yet:

- **Search/browse** needs a way to list/search courses — new endpoint,
  e.g. `GET /courses` (with a search/filter query param).
- **Course detail** needs a single-course lookup — new endpoint, e.g.
  `GET /courses/{id}`.

These are new backend work, in scope for this sprint (not just frontend).
The deferred "no `LIMIT` on courses-per-skill" item from Sprint 2 becomes
relevant to the new browse endpoint too — pagination/limits should be
decided as part of building it, not left open twice.

## Error handling

Per DESIGN.md's "honest, never manufactured" principle: failed API calls
(backend unreachable, unknown goal → the existing 404 behavior of
`POST /paths`) render an inline error state. No silent fallback to fake or
placeholder data.

## Build order

1. Shared layout/nav + Tailwind theme (colors, typography, mobile-first
   base styles per DESIGN.md sections 3 and 7).
2. The core loop: onboarding → dashboard (goal input through path view) —
   proves the real `POST /paths` integration end to end.
3. Search/browse, course detail, profile, landing page — in roughly that
   order, but each is independent of the others once the core loop and
   shared layout exist.

## Open items carried into the implementation plan

- Exact shape of the new `GET /courses` / `GET /courses/{id}` endpoints
  (query params, response schema, pagination/limit approach) — to be
  resolved in the implementation plan, not this design doc.
- Exact `localStorage` schema for `skillpath.currentPath` — to be resolved
  in the implementation plan.
