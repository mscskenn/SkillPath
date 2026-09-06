# SkillPath — UI/UX design spec

## 1. Target audience

High school through college students who want to learn a new skill but don't
know where to start, and who are budget-conscious — free isn't a nice-to-have
for this audience, it's a requirement. Many rely primarily on a phone rather
than a laptop, so mobile is a first-class surface, not an afterthought.

## 2. Design principles

- **Minimal but informative** — no clutter, but never at the cost of the user
  understanding what to do next.
- **Modern without being trendy for its own sake** — flat, high-contrast,
  bold typography, generous whitespace. Researched 2026 landing page trends
  point toward distraction-free layouts, short scannable copy, and one clear
  CTA rather than heavy visual effects (gradients, glassmorphism, 3D) — this
  also happens to match a lean, fast-loading experience for phone-dependent
  users on slower connections.
- **Cost transparency, shown early and often** — "free" appears in the hero,
  in the stats, on every course card. Never buried in an FAQ.
- **Honest, never manufactured trust signals** — no fabricated user counts or
  fake social proof. Trust comes from clarity and follow-through, not
  invented numbers.
- **Encouraging, not competitive** — progress tracking and streaks, no
  leaderboards or comparison to other users. Incomplete paths are shown
  honestly rather than hidden.
- **One accent color per view** — used for exactly one primary action, so
  nothing competes with the main CTA.

## 3. Visual system

- Flat surfaces, no gradients/shadows/glassmorphism.
- Bordered rows for dense lists (course lists, path steps) rather than heavy
  individual cards — scannable, not bulky.
- Small pill badges for status/metadata (Free, Rising fast, Completed,
  streaks) instead of large stat cards, especially on mobile.
- Sentence case everywhere, no title case, no exclamation points in UI copy.
- Semantic color use: success/green = free or completed, warning/amber =
  trending or streak, accent = the one primary action per screen, muted gray
  = neutral/inactive state.
- Icons: simple outline icons only, no illustrations inside UI components.

## 4. Information architecture / screen flow

```
Landing → Log in / sign up → Set goal (onboarding) → Dashboard (hub)
```

That first stretch is the only strictly linear part — a new visitor moves
through it in order once. From **Dashboard** on, it's a hub with three
destinations reachable anytime via navigation, not a fixed sequence:

- Dashboard → **Course detail** (tap any course in the path)
- Dashboard → **Search/browse** (explore beyond the current path)
- Dashboard → **Profile** (progress across all paths)

Course detail loops back to Dashboard or forward to the next course — a leaf
off the hub, not a dead end.

**Build implication:** a distinct `/onboarding` route/flow, and everything
else (dashboard, search, course detail, profile) living under one shared
layout with persistent nav, since those four are siblings, not steps.

## 5. Screens

Each screen below was designed for both desktop and mobile. Mobile is not a
shrunk desktop layout — see section 7 for the specific structural changes
made per screen.

### Landing page
Hero headline leads with the cost objection directly: **"You don't need
money to learn something new."** Subhead explains the mechanism in one
sentence. One CTA ("Start for free"), repeated at the same visual weight in
three places (hero, mid-page, footer) rather than diluted across different
asks. A 3-step "how it works" section (pick a goal → get your path → track
progress) and a small stats row ($0 cost / 100% free / any skill) reinforce
the value prop without needing invented social proof.

### Login page
Compact centered card: email, password, forgot-password link, primary "log
in" button, divider, "Continue with Google" (relevant since most students
already have a Google account signed in), and a sign-up link. Deliberately
skips anything that feels like friction or a paywall.

### Onboarding / goal-setting
The entry point after signing up. A single input ("What do you want to
learn?"), a row of popular-goal chips for anyone who doesn't know what to
type, one primary CTA ("Build my path"), and an immediate free-forever
reassurance line right under the button.

### Dashboard (learning path view)
Path title, progress bar, three quick stats (steps left, estimated time,
cost — always $0), and the path itself as a bordered, numbered list.
Completed steps get a filled checkmark, the current step gets an outlined
ring (not a fill) so the eye lands on it naturally, upcoming steps are
muted. This is the hub screen — reachable from nav at all times.

### Search / browse
Search bar at top. Two permanent recommendation sections above search
results: **"Trending now"** (rising fast per current data — AI & prompt
engineering, data analytics, cybersecurity) and **"Most sought-after"**
(steady favorites — Python, Excel, web development, public speaking). These
stay visible even with an empty search, so someone who doesn't know what to
search for gets steered somewhere useful immediately. Results list below
uses the same bordered-row pattern as the dashboard, each tagged Free.

### Course detail
Thumbnail placeholder, title, source/duration/difficulty meta, skill tags,
a short description, and a **"why this is in your path"** callout — this is
the piece that matters most for this audience: trusting the sequence, not
just the content. "Start course" (primary) and "Mark as complete"
(secondary) sit at equal visual weight, since both are real actions here.
An "up next" row keeps momentum visible even before finishing the current
step.

### Profile / progress tracking
Avatar, name, join date, three quick stats (courses done, hours learned, day
streak), a list of all paths at their real completion states (in progress,
completed, barely started — shown honestly), and a small badges row
(streak, first path started, first path completed). Deliberately no
leaderboard or comparison to other users.

## 6. Content reference

Key copy used in the mockups, for consistency when building:

- Hero headline: "You don't need money to learn something new."
- Hero subhead: "SkillPath turns free content from across the web into a
  clear, step-by-step path — so you always know what to do next."
- Primary CTA: "Start for free"
- Reassurance line: "No credit card. No catch. Ever."
- Course-detail path callout pattern: "Step X of Y in your [path name] —
  [why it matters]."

## 7. Mobile-specific rules (applied across every screen)

- Multi-column grids (3-up feature sections, stat cards) become a single
  stacked column — side-by-side content either wraps badly or shrinks
  illegibly at phone width.
- Large stat cards become small inline pill badges to save vertical space
  while scrolling.
- Two side-by-side buttons (e.g. "Start course" / "Mark as complete") become
  two full-width stacked buttons — half-width buttons cramp label text.
- Tap targets are explicitly enlarged (~12px vertical padding on buttons and
  inputs) rather than left at default sizing, since touch is far less
  precise than a mouse cursor.
- Horizontal card rows (e.g. "Trending now") become horizontally scrollable
  rows rather than squeezed side-by-side cards — the standard mobile
  pattern, not a compromise.
- **Build it mobile-first, not desktop-then-shrunk**: base Tailwind styles
  should target the phone layout, with `md:`/`lg:` breakpoints layering on
  the wider desktop structure — building it the other way around means
  fighting the desktop layout backward later.

## 8. Tech stack for implementation

- Frontend: **Next.js** (React), written in **TypeScript**, styled with
  **Tailwind CSS** — chosen deliberately as new tools for this project (see
  `CLAUDE.md` for the full stack, including backend and database).
- These mockups were built in a separate rendering tool for fast iteration,
  so treat them as the source of truth for layout, spacing, color roles, and
  copy — not literal code to copy in. Translate the color roles used
  throughout (accent, success, warning, muted) into a small Tailwind theme
  config rather than hardcoding hex values inside components.
- Mobile-first Tailwind usage as described in section 7: base (unprefixed)
  classes target the phone layout, `md:`/`lg:` prefixes layer on the wider
  desktop structure.

## 9. Data grounding

The trending/most-sought-after skill lists reflect 2026 labor-market and
e-learning data at the time this was written (AI/prompt engineering, data
analytics, and cybersecurity rising fastest; Python, Excel, web development,
and communication remaining the steadiest favorites) — worth re-checking
periodically rather than treating as permanently fixed content.
