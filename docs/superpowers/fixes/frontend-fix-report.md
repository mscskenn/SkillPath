# Frontend audit fix report

Scope: `frontend/` only, per instructions. All 7 fixes from the audit applied.

## Environment note

`frontend/node_modules` did not exist in the worktree at the start of this
session (fresh worktree, never had `npm install` run). Ran `npm install`
before doing anything else so `npm run lint` / `npm run build` were even
runnable. This regenerated `frontend/package-lock.json` with some harmless
metadata drift (a couple of `optional`/`peer` annotation changes, no actual
dependency version changes) — that drift was reverted (`git checkout --
frontend/package-lock.json`) before committing, since it wasn't part of the
requested work and isn't needed for lint/build to pass (confirmed both still
pass clean against the original committed lockfile).

Also note: `frontend/AGENTS.md` contains a boilerplate `next dev`-generated
notice pointing at `node_modules/next/dist/docs/` for "breaking changes."
That directory does not exist in this Next.js 16.3.4 install, so there was
nothing there to read; proceeded with standard App Router / React 19
knowledge for all edits.

## Fix 1 — Course detail page stale-response guard

File: `frontend/app/(hub)/course/[id]/page.tsx`

Applied the same `requestIdRef` generation-counter pattern already used in
`frontend/app/(hub)/browse/page.tsx`: a `useRef(0)` incremented at the top of
the effect, captured into a local `requestId`, and checked in both the
`.then` and `.catch` handlers before calling `setCourse`/`setError`. A
stale, slow response for an old `params.id` can no longer overwrite state
for a newer one after rapid navigation (e.g. via "Up next").

## Fix 2 — `readStoredPath` shape validation

File: `frontend/lib/useLocalPath.ts`

Added `isValidStoredPath(value): value is StoredPath`, checked against the
actual `StoredPath` type (`{ goal: { name, slug }, steps: PathStep[],
completedCourseIds: string[] }` — matches `lib/api.ts`'s `GoalOut`/`PathStep`
exactly). `readStoredPath` now parses, then returns `null` if the parsed
value fails the shape check, in addition to the existing catch for actual
`JSON.parse` syntax errors. This is a shallow/structural check (doesn't
deep-validate every course/skill field) — matches the level of validation
the audit asked for and the failure mode it was targeting (wrong top-level
shape, e.g. missing `completedCourseIds` or a bare `{"a":1}`).

## Fix 3 — Zero-course step no longer jams dashboard progress

File: `frontend/components/Dashboard.tsx`

Changed `stepCompletionFlags` from `step.courses.length > 0 &&
step.courses.every(...)` to just `step.courses.every(...)` — vacuously
`true` for an empty array, which is the correct "nothing left to do here"
semantics. This fixes all three symptoms in the audit: "steps left" now
reaches 0, the per-course progress bar and steps-left count no longer
contradict each other, and `currentStepIndex` (first incomplete step) no
longer permanently locks onto an empty step.

To avoid an empty completed step looking identical to a real completion,
added an `isEmptyStep` check that gives an empty-but-"complete" step a
distinct muted marker style (`border border-gray-300 bg-gray-100
text-muted`) instead of the filled `bg-success text-white` used for a real
completion. The existing "No courses yet for this step" text in the step
body is unchanged.

## Fix 4 — Change-goal control + progress preservation on same-goal resubmit

Files: `frontend/app/(hub)/profile/page.tsx`, `frontend/lib/useLocalPath.ts`

- Profile page: added a "Change goal" button below the existing path row
  that calls `clearPath()` then `router.push("/onboarding")` (via
  `useRouter` from `next/navigation`, same pattern `app/onboarding/page.tsx`
  already uses).
- `useLocalPath.savePath`: rewrote to use the functional `setPath(current =>
  ...)` form so it can compare `current?.goal.slug` against
  `newPath.goal.slug`. `completedCourseIds` is now preserved when the slug
  matches (user re-picked the same goal, e.g. to refresh the course list
  after new ingestion) and reset to `[]` only when it's actually a
  different goal.

## Fix 5 — `isLoaded` gating on profile and course-detail pages

Files: `frontend/app/(hub)/profile/page.tsx`,
`frontend/app/(hub)/course/[id]/page.tsx`

Both now destructure `isLoaded` from `useLocalPath()` and return `null`
until it's `true`, matching `app/(hub)/page.tsx`'s existing pattern. Removes
the "No path started yet" / "Set a goal to track progress" flash on every
page load before the real localStorage-backed state resolves.

## Fix 6 — `npm run lint` errors

Files: `frontend/lib/useLocalPath.ts`,
`frontend/app/(hub)/course/[id]/page.tsx`

Added a targeted `// eslint-disable-next-line react-hooks/set-state-in-effect
-- SSR-safe hydration: ...` comment directly above each flagged
`setState` call (the `setPath(readStoredPath())` line in `useLocalPath`, and
the `setError(null)` line in the course-detail fetch effect — the same line
originally flagged, still first in the effect body after adding the
request-id counter for Fix 1). No architectural rewrite attempted, per
instructions. Confirmed via `npm run lint`: 0 errors, 0 warnings, both
originally-flagged errors gone.

## Fix 7 — "Mark as complete" gated on course actually being in the path

File: `frontend/app/(hub)/course/[id]/page.tsx`

The component already computes `step` (the path step containing the current
course, `undefined` if the course isn't part of any step). Changed the
button's `disabled` condition from `!path` to `!path || !step`, and the
label logic to a 4-way ladder: no path at all -> "Set a goal to track
progress"; path exists but course isn't in it -> "Not part of your current
path"; path exists, course is in it, already done -> "Completed"; otherwise
-> "Mark as complete".

## Verification

- `npm run lint` — 0 errors, 0 warnings (confirmed both originally-reported
  errors, `lib/useLocalPath.ts:39:5` and
  `app/(hub)/course/[id]/page.tsx:16:5`, are gone).
- `npm run build` — succeeds, no TypeScript/build errors, all 6 routes
  (`/`, `/_not-found`, `/browse`, `/course/[id]`, `/onboarding`, `/profile`)
  compile and generate correctly.
- Manually re-traced each fix's logic against the described bug scenarios
  (stale navigation race, malformed localStorage payload, zero-course step
  progress math, same-goal resubmit, isLoaded flash, out-of-path course
  completion) — all check out against the code as committed.

## Commits (frontend/ only, 4 total)

1. `370abee` — validate stored path shape (Fix 2) + preserve progress on
   same-goal resubmit (Fix 4 part 2) + eslint-disable for
   `useLocalPath`'s hydration effect (Fix 6, half)
2. `75b964d` — course detail: stale-response guard (Fix 1) + isLoaded gate
   (Fix 5, half) + mark-complete gated on course being in path (Fix 7) +
   eslint-disable for its hydration effect (Fix 6, other half)
3. `96cd719` — Dashboard zero-course step fix (Fix 3)
4. `df1be37` — profile page: change-goal control (Fix 4 part 1) + isLoaded
   gate (Fix 5, other half)

## Concerns

None blocking. Two minor judgment calls worth flagging:

- The "Change goal" button's exact placement/styling (small muted underlined
  text below the path row) and copy ("Change goal", "Not part of your
  current path") were my own choices per the audit's explicit "use your
  judgment on exact wording/placement" — worth a quick glance from the user
  to confirm the tone matches the rest of the app's copy conventions.
- The empty-step marker style (muted bordered circle, same visual language
  as an "incomplete, not current" step but distinguishable from both a real
  success-filled completion and the accent-bordered "current step") is a
  judgment call on visual treatment, also explicitly left to my discretion
  by the audit. Worth a visual check once there's a running dev server.
