# DevPulse — Design System

The visual + interaction language for DevPulse. Grounded in the actual implementation
(`frontend/src/index.css`, `LandingPage.jsx`, `components/DigestSample.jsx`). Both the web UI
and the digest **email** follow this system.

---

## 1. North star

**A developer's daily brief.** Broadsheet-editorial meets developer tool: the serif pedigree of
a quality newspaper (Anthropic / CrewAI), the precision of a terminal, on a calm white page.
Restraint over decoration. Asymmetry over centered blocks. Truthful over flashy — every number
shown reflects real backend data.

Adjectives: editorial, composed, posh, precise, quiet.

---

## 2. Color tokens

Defined in `index.css` under `@theme`. Light theme only.

| Token | Value | Use |
|-------|-------|-----|
| `--color-page` | `#FFFFFF` | page background |
| `--color-tint` | `#F9F9F8` | subtle section/tint bands |
| `--color-ink` | `#1A1A1A` | primary text, dark buttons |
| `--color-muted` | `#6B7280` | secondary text, mono labels |
| `--color-hairline` | `#EAEAEA` | rules, borders, dividers |
| `--color-accent` | `#5B5BD6` | THE brand indigo — links, italic emphasis, focus, pills |
| `--color-ok` | `#16A34A` | additions, rising momentum |
| `--color-warn` | `#D97706` | attention |
| `--color-bad` | `#E11D48` | deletions, declining momentum |
| `--color-conflict-bg` / `-fg` | `#FEF3C7` / `#92400E` | Conflict pill |

**Accent discipline:** indigo is a scalpel, not a bucket. Wordmark, links, one italic word per
headline, focus rings, small labels. Never large indigo fills.

**Ambient glows:** faint indigo/violet radial gradients on `body` (`background-attachment: fixed`)
so the page is never flat white and glass has something to refract. They stay in the viewport as
you scroll.

---

## 3. Typography

Three families (loaded via `@import` in `index.css`):

| Family | Token | Role |
|--------|-------|------|
| **Playfair Display** (serif) | `--font-display` / `.serif` | display headlines; one **italic + indigo** word for emphasis |
| **Inter** (sans) | `--font-body` | body, lede paragraphs |
| **JetBrains Mono** (mono) | `--font-mono` / `.mono` | labels, section numbers, repo names, stat numerals, metadata, buttons, datelines |

Rules:
- Headlines are **serif, left-aligned, large** (44–72px). Emphasis word: `italic` + `--color-accent`.
- The **mono** face is the "developer" signal — use it for anything data/label/meta
  (`01 — ACCURATE`, `me/aria #124`, `+254 −120`, `DAILY BRIEF`). Uppercase + 0.05em tracking.
- Body/lede in Inter, ~20px, max ~55ch line length.
- Numerals use `tabular-nums` in stat contexts.

---

## 4. Layout

- **Container:** `max-w-[1200px]`, side padding `px-6 md:px-20` (`PAGE` const in LandingPage).
- **Grid:** 12-col (`grid-cols-12`), `gap-8`. Asymmetry lives *inside* the grid — never random.
- **Feature-row skeleton** (identical for all, only the card side flips):
  col 1–2 = mono `0X — LABEL`; a 5-col heading+lede; a 4-col example card offset to the opposite
  side. Rows alternate card side (01 right, 02 left, 03 right, 04 left) on fixed columns → rhythmic.
- **Rhythm:** every section separated by a `1px #EAEAEA` hairline, uniform vertical padding
  (`py-24 md:py-32`). Metronomic, not gappy.
- **Bleed:** the hero digest card may crop off the right edge for an editorial, off-center feel.

---

## 5. Components & primitives

CSS primitives (`index.css @layer components`):
- `.serif` — Playfair, -0.01em tracking.
- `.mono` — JetBrains Mono, 12px, uppercase, 0.05em.
- `.rule` — top hairline.
- `.btn-dark` — solid `#1A1A1A` pill, white mono label, hover opacity. **The only button style.**
- `.glass` — frosted card: `rgba(255,255,255,0.45)` + `backdrop-blur(16px) saturate(150%)`,
  hairline-white border, soft indigo drop-shadow. Sits over the ambient glows.
- `.glass-nav` — sticky top nav, translucent + blur, hairline bottom.

React building blocks:
- `SignInPill` (LandingPage) — the single CTA. Signed-out → Clerk `SignInButton` modal
  (`forceRedirectUrl="/dashboard"`); signed-in → "Open dashboard" → `/dashboard`.
- `Reveal` (LandingPage) — framer-motion scroll reveal: `opacity 0 → 1`, `y 26 → 0`, `once`,
  ease `[0.22,1,0.36,1]`. Wrap any section that should animate in.
- `Feature` — one editorial row (props: `num,label,heading,accent,tail,lede,card,flip`).
- `MiniCard` — a `.glass` example card used inside features.
- `DigestSample` (`components/DigestSample.jsx`) — the macOS-window recreation of the digest
  email; **the canonical visual reference** for the email. Reused on landing + dashboard.

---

## 6. Motion

`framer-motion`, subtle and once-only:
- Section content fades + rises on scroll into view (`Reveal`, `viewport once`, `-80px` margin).
- Hero copy + digest card animate in on load (`animate`, slight `scale` on the card).
- Buttons: opacity on hover. No bounce, no parallax excess. Motion should feel composed.

---

## 7. Grounding rules (non-negotiable)

The UI must only show data the backend actually produces. Reference: `DigestContext` /
`services/email.py` / `clients/github.py`.
- **Allowed stats:** commits, PRs opened, PRs merged, issues, reviews, streak, momentum
  (rising/steady/declining), and waiting-PRs (repo, #, title, +add/−del, files,
  `Conflict` / `Review requested` / `Draft`).
- **Forbidden:** any CI/"build success %" metric — not fetched (deferred). Mentions/review
  threads — not fetched. Do not invent data in mockups.

---

## 8. Email must mirror this (Milestone 11)

The digest email (`backend/app/services/email.py::_build_digest_html`) predates this system and
must be refactored to match: serif masthead + dateline, mono section labels + metadata, indigo
accent, hairline rules, the same composed rhythm — while staying **email-safe** (tables, inline
styles, web fonts with system fallback) and **fixed-light / inversion-proof** (`color-scheme`
lock). `DigestSample.jsx` is the target look.

---

## 9. Interaction inventory

Single CTA everywhere: **Sign in with GitHub** (Clerk modal → `/dashboard`). Wordmark → `/`
(router `Link`). Footer → GitHub repo. Dashboard (WIP) exposes exactly two controls: frequency
(`off/6h/12h/daily/weekly`) and tracked repos — no other knobs. No content-type filters.

---

## 10. Do / Don't

**Do:** whitespace, hairlines, one italic-indigo word per headline, mono for data, glass on
cards over glows, truthful numbers.
**Don't:** center hero blocks, glass-on-everything (muddies white), large indigo fills, gradient
text, drop shadows on text, fake metrics, more than one button style.
