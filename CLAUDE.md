# CLAUDE.md — PimPam Development Guide

This file guides Claude Code when working on PimPam, an open-source, ad-free, human-first social network.

> **Backend code standards, testing patterns, and architecture details** are defined in the `/backend-engineer` skill. This file covers project identity, setup, design language, current status, and the frontend roadmap.

---

## Project Overview

**The hypothesis:** Social networks are harmful because of how they're built and who they're built for — not because social connection itself is harmful. We're removing the specific structural incentives that cause most of the damage — algorithmic amplification, surveillance capitalism, centralised control — and seeing what grows in their place.

PimPam is a community-owned social platform built as an ethical alternative to corporate social media. No algorithmic feeds, no ads, no data exploitation, governed by its community.

**Core features:**
- Chronological feed (posts from followed users, time-ordered — never algorithmic)
- Communities (topic-based spaces, similar to subreddits)
- Direct messaging with end-to-end encryption (server must never read plaintext)
- Karma system for contribution recognition

**License:** AGPL-3.0. All modifications must remain open-source, including when run as a network service.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React + Vite (PWA) |
| Backend | Python + FastAPI |
| Database | PostgreSQL via SQLAlchemy 2.0 (async) |
| Migrations | Alembic |
| Federation | ActivityPub (HTTP Signatures, WebFinger) |
| Real-time | WebSockets via FastAPI + Redis pub/sub |
| Auth | bcrypt (passlib, cost 12), JWT (python-jose), TOTP 2FA |
| Encryption | TLS 1.3 in transit, AES-256 at rest, E2E for DMs (client-side keys) |
| Search | Meilisearch |
| Storage | S3-compatible (MinIO dev, Cloudflare R2 prod) |
| Rate limiting | slowapi |
| HTTP client | httpx (federation delivery) |
| Linting | Ruff + Black (backend), ESLint + Prettier (frontend) |

---

## Development Setup

```bash
# Backend
uv venv && source .venv/bin/activate
uv pip install -r requirements.txt
cp .env.example .env          # Edit with your DB credentials and secrets
alembic upgrade head
uvicorn app.main:app --reload  # Docs at http://localhost:8000/docs

# Frontend
cd client && npm install && npm run dev

# Tests
pytest                         # Backend (uses SQLite in-memory, no Postgres needed)
npm test                       # Frontend

# Dependencies — never edit requirements.txt by hand
uv pip compile requirements.in -o requirements.txt
uv pip install -r requirements.txt
```

Docker Compose provides PostgreSQL, Redis, and Meilisearch: `docker compose up -d`

---

## Architecture Principles (non-negotiable)

1. **No algorithmic ranking.** Feeds are always chronological. Never reorder content by engagement metrics.
2. **No ads, no tracking, no behavioral analytics.** Collect only the minimum data needed.
3. **Privacy by design.** Direct messages are E2E encrypted. The server stores only ciphertext.
4. **AGPL-3.0.** Never introduce dependencies that would conflict with this license.
5. **Accessibility over performance tricks.** Prefer clear, accessible code over clever optimizations.
6. **Simplicity first.** Don't over-engineer. Build the minimum that works correctly and securely.

---

## What NOT to Build

- Algorithmic content ranking or recommendation engines
- Ad serving or targeting infrastructure
- Behavioral analytics or user profiling
- Any feature that monetizes user data
- Any proprietary components (must stay AGPL-compatible)
- Shadow banning or opaque moderation (all moderation must be transparent and appealable)

---

## Data Protection (GDPR)

- Collect only minimum necessary data; never sell, share, or repurpose user data
- Technical logs retained max 30 days
- Do NOT collect: location, device fingerprints, browsing history, contact lists, biometrics, behavioral analytics
- Users must be able to: access, correct, delete, export, restrict, and object to their data

---

## Code Standards (summary)

Backend standards are fully defined in `/backend-engineer`. Key points for all contributors:

- **Backend**: Ruff + Black; type hints everywhere; async route handlers; Pydantic for all request/response validation
- **Frontend**: ESLint + Prettier; semantic HTML; WCAG 2.1 AA accessibility
- **API design**: FastAPI is the single source of truth; version prefix `/api/v1/`; never return raw ORM objects
- **Testing**: `pytest` + `httpx.AsyncClient` (backend); tests for every new component/behavior (frontend)
- **PRs**: one feature/fix per PR; branch naming `feature/`, `fix/`, `docs/`; 1+ maintainer review (2 for security)
- **Security reports**: `security@pimpam.org` (not public GitHub issues)

---

## Design Language & UX

These decisions are locked in. All frontend work must follow them.

### Navigation model

```
Mobile — fixed bottom tab bar (5 tabs):
  [Feed]  [Communities]  [Messages]  [Notifications]  [Profile]

Desktop (>= 1024px) — left sidebar with the same 5 items as vertical nav links.
No bottom bar on desktop. Content area fills the remaining width.
```

Each tab has a thin header bar:

| Tab | Left | Right |
|---|---|---|
| Feed | PimPam logo | search icon + compose button |
| Communities | "Communities" | search pill ("Search communities...") |
| Messages | "Messages" | compose new DM icon |
| Notifications | "Notifications" | mark-all-read icon |
| Profile | `@username` | settings gear |

**Badges:** unread DM count on Messages tab; unread notification count on Notifications tab.

### Stories

- **No "seen by" list.** Zero behavioural tracking.
- **No countdown timer.** Stories disappear when they expire. No urgency UI.
- **User-configurable duration.** Default 24h; author picks 12h / 24h / 48h / 7 days.
- **Image + optional caption** (max 200 chars). No video in v1.
- **Moderation grace period.** Reported stories soft-deleted but retained 48h for mod review.

Stories row in Feed tab — horizontal scroll of circular avatars. Coloured ring = unseen story. Own avatar shows `+` to compose.

### Feed content

Single unified chronological stream combining:
1. Posts by users the viewer follows
2. Posts in communities the viewer has joined

A post matching both appears only once.

### Search

- **Feed tab:** magnifying glass icon expands a full-width input bar with smooth animation.
- **Communities tab:** tappable pill ("Search communities...") — more prominent affordance.

### Communities tab layout

```
+--------------------------------------+
| Communities       [Search communities]|
+--------------------------------------+
| Your communities                     |
| [c/design] [c/music] [c/tech]  ->   |  <- horizontal scroll
+--------------------------------------+
| Discover          [Popular] [New]    |
|  c/philosophy   1.2k members   [+]  |
|  c/cooking        890 members  [+]  |
+--------------------------------------+
```

### Aesthetic direction

- **Mobile-first.** Desktop adapts via sidebar, not a different layout.
- **Familiar over novel.** Borrow proven patterns (Instagram stories/tabs, Reddit communities/votes, WhatsApp messages).
- **Minimal chrome.** Content is the UI.
- **No dark patterns.** No countdown timers, no seen-by, no auto-play, no read-receipt pressure.
- **Neutral palette + one accent colour** for interactive elements.
- **DMs are 1-on-1 only** in v1. No group chats.

---

## File Layout

```
pimpam/
├── app/
│   ├── main.py                     # App entry + all routers
│   ├── api/
│   │   ├── v1/                     # REST API (/api/v1/*)
│   │   │   ├── auth.py             # register, login, refresh, totp/*
│   │   │   ├── users.py            # profiles, follow/unfollow
│   │   │   ├── feed.py             # chronological feed
│   │   │   ├── posts.py            # CRUD + vote + boost + share
│   │   │   ├── comments.py         # nested comments + reactions
│   │   │   ├── communities.py      # CRUD + join/leave
│   │   │   ├── moderation.py       # bans, appeals, mod promotion
│   │   │   ├── search.py           # Meilisearch full-text
│   │   │   └── messages.py         # E2EE messages
│   │   ├── ws.py                   # WS /ws?token=<jwt>
│   │   └── federation/             # ActivityPub endpoints
│   ├── federation/                 # AP protocol logic
│   ├── models/                     # SQLAlchemy ORM models
│   ├── schemas/                    # Pydantic request/response models
│   ├── crud/                       # DB queries
│   ├── core/
│   │   ├── config.py               # pydantic-settings + .env
│   │   ├── security.py             # JWT, bcrypt
│   │   ├── dependencies.py         # DBSession, CurrentUser
│   │   ├── logging.py              # Structured logging setup
│   │   ├── redis.py                # Redis client + pub/sub
│   │   ├── search.py               # Meilisearch integration
│   │   └── storage.py              # S3-compatible media
│   └── db/
│       ├── base_class.py           # DeclarativeBase
│       ├── base.py                 # Model imports for Alembic
│       └── session.py              # Async engine + session factory
├── alembic/                        # Migration files
├── tests/
│   └── conftest.py                 # Fixtures (SQLite in-memory)
├── client/                         # React PWA frontend
│   ├── src/
│   │   ├── api/client.js           # Axios + token refresh
│   │   ├── pages/
│   │   └── components/
│   └── vite.config.js              # Dev proxy -> localhost:8000
├── requirements.in                 # Abstract deps (edit this)
├── requirements.txt                # Pinned lockfile (uv-generated)
├── docker-compose.yml              # PostgreSQL, Redis, Meilisearch
└── CLAUDE.md
```

---

## Current Status

The backend is complete. **399 tests, 88% coverage**.

**Implemented:**
- Auth: register, login, refresh (bcrypt + JWT, rate-limited)
- 2FA (TOTP): setup, verify, disable; AES-encrypted secrets at rest
- Password reset: link mode (15 min) or code mode (6-digit, 10 min); rate-limited 3/hour
- Logout + change password (both bump `token_version` to revoke all refresh tokens)
- Email verification: token emailed on register (60-min, single-use, SHA-256 stored); unverified accounts auto-deleted after 30 days
- Account deletion: 7-day grace period with cancel option; hourly task executes (posts/comments anonymised, messages deleted, user hard-deleted)
- GDPR: data export endpoint; consent log at registration; 30-day consent purge
- User profiles with follower/following counts, `is_following` flag
- Unified chronological feed (followed users + joined communities, cursor-paginated)
- Stories: ephemeral posts with configurable duration; no seen-by tracking; hourly cleanup
- Posts: create, edit (1h window), delete, vote, karma, boost (AP Announce), share
- Comments: nested (5 levels), sort latest/top, reactions (agree/love/misleading/disagree), mod remove/restore
- Communities: create, list, join/leave; two-tier karma (global + per-community); auto role promotion at 50 community karma
- Moderation: role hierarchy (member -> trusted_member -> moderator -> senior_mod -> owner); ban proposals (10-vote consensus), appeals, mod promotion, ownership transfer
- Follow/unfollow (local + federated, pending state)
- Direct messages: E2EE ciphertext only, inbox, conversation thread, mark as read
- Friend groups with group-scoped post visibility
- Rate limiting on all write endpoints and feed
- Media uploads: JPEG/PNG/WebP/GIF -> WebP, EXIF strip, resize, S3 storage
- Search: full-text via Meilisearch (posts, users, communities)
- ActivityPub federation: WebFinger, NodeInfo, Actor, Inbox, Outbox, HTTP Signatures
- WebSocket real-time: new_post, new_comment, new_message, karma_update, notifications via Redis pub/sub; typing indicators
- Notifications: 14 event types, grouped, per-type opt-out, real-time WS push
- Multi-image posts (behind `MULTI_IMAGE_POSTS_ENABLED` flag)

**Not yet implemented:**
- React frontend (client/ skeleton only — see Frontend Roadmap below)
- Multiple images per post UI
- NCMEC content hash-matching
- BYOS (user-provisioned storage)
- Karma privilege thresholds beyond mod eligibility
- Admin layer (site-wide moderation, global bans — required before public launch)
- Mod rewards / separate moderation karma track

---

## Planned Improvements

1. ~~**Fix comment listing N+1**~~ DONE — batch queries, 3 DB round-trips regardless of page size.
2. ~~**Rate limit comment creation**~~ DONE — `1/30 seconds` per user.
3. ~~**Expand search**~~ DONE — users + communities indexes added.
4. **Admin layer** — site-wide admin flag, global bans, user suspension, platform content removal. Required before public launch.

---

## Frontend Roadmap

The backend is complete. The `client/` directory is a React + Vite PWA skeleton. This section is the authoritative checklist for all frontend work.

### What already exists (working)

| File | State |
|---|---|
| `src/api/client.js` | Complete — Axios + Bearer token + silent refresh interceptor |
| `src/App.jsx` | Skeleton — 3 routes only, no nav shell |
| `src/pages/Login.jsx` | Complete — functional form |
| `src/pages/Register.jsx` | Mostly complete — missing GDPR consent checkboxes |
| `src/pages/Feed.jsx` | Functional — missing compose button and post actions |
| `src/components/PostCard.jsx` | Skeleton — no author, no votes, no comments |

---

### Phase 0 — Backend prerequisites (complete before any frontend work)

**0a. Stories backend**

- `app/models/story.py` — `Story` model: `id`, `author_id` (FK -> users, CASCADE), `image_url`, `caption` (nullable, String 200), `expires_at` (DateTime, indexed), `is_removed` (bool, default false), `created_at`
- `app/db/base.py` — import Story for Alembic
- `app/api/v1/stories.py` — 4 endpoints:
  - `POST /stories` — create (auth required; image from prior upload, optional caption, `duration_hours` default 24, max 168)
  - `GET /stories/feed` — from followed users + joined communities, not expired, desc; **no `expires_at` in response**
  - `DELETE /stories/:id` — author only, 204
  - `POST /stories/:id/report` — soft-delete (`is_removed = true`), retain 48h for mod review
- `app/main.py` — register router; add hourly cleanup for expired stories
- Migration + tests covering: create, feed, expiry, early delete, report, auth, feed exclusion

**0b. Unified feed query**

Update `GET /feed` to return posts from followed users + joined communities, deduplicated (SQL OR, not UNION), cursor-paginated. Add tests for community posts in feed and dedup.

---

### Phase 1 — Infrastructure

**App shell & routing**
- Bottom tab bar (mobile, 5 tabs) + left sidebar (desktop >= 1024px)
- Per-tab header bars (see Design Language)
- `React.lazy` + `<Suspense>` for route-level code splitting
- `AuthContext` — user, tokens, login/logout; hydrate via `GET /users/me`; redirect on 401
- `NotificationContext` — unread counts from WS events; drives tab badges
- `WSContext` — single WS connection after login; typed event dispatch

**Split `api/client.js` into domain modules:** auth, users, posts, comments, communities, moderation, messages, notifications, search, friendGroups

**Shared UI components:** Avatar, Button (primary/secondary/ghost/danger + loading), Modal (focus trap, Escape), Toast (useToast hook, auto-dismiss 4s), Spinner/Skeleton, ErrorBoundary, InfiniteList (IntersectionObserver), RelativeTime

---

### Phase 2 — Auth flows

- **Register**: add 3 consent checkboxes (ToS, Privacy, Age 13+); show "check your email" interstitial after success
- **Email verification**: `/verify-email?token=` page; persistent banner for unverified logged-in users with resend button
- **TOTP 2FA**: if login returns `requires_totp: true`, redirect to `/login/totp` for 6-digit code
- **Password reset**: `/forgot-password` (email input, always shows same message) + `/reset-password?token=` (new password form)
- **Logout**: `POST /auth/logout`, clear AuthContext, redirect to `/login`

---

### Phase 3 — Feed & post compose

**Stories row** (top of Feed tab)
- Horizontal avatar scroll; coloured ring = unseen; own avatar with `+` to compose
- Compose: image picker -> preview -> caption (200 chars) -> duration selector -> `POST /stories`
- Viewer: full-screen, swipe navigation, no progress bar/countdown/seen-by

**Post feed**
- Compose FAB -> Modal with: title, content, URL, community selector, visibility (public/followers/friend group), image upload
- Empty state: onboarding prompts ("Discover communities", "Find people to follow")
- WS `new_post`: show "New posts available" banner (no auto-insert)

---

### Phase 4 — PostCard (complete rewrite)

Author avatar + @username, community badge, title (with external URL indicator), content snippet (truncate ~3 lines), images (+N badge), vote buttons (optimistic UI), comment count, boost button, RelativeTime, overflow menu (edit within 1h / delete / mod remove)

---

### Phase 5 — Post detail page (`/posts/:id`)

Full content, image gallery + lightbox, vote/boost/share, edit (1h window with countdown), delete (confirm modal), comment thread: sort latest/top, nested 5 levels with left-border indent, reactions, inline reply form, fixed compose box. WS `new_comment` appends live.

---

### Phase 6 — User profile (`/@:username`)

Header (avatar, name, bio, follower/following/karma counts), follow/unfollow button, 3 tabs (Posts | Followers | Following), edit profile (own: display name, bio, avatar upload via `PATCH /users/me`)

---

### Phase 7 — Communities

**Tab**: "Your communities" (horizontal scroll + "+ Create" chip) + "Discover" (Popular | New sort, join buttons)
**Community page** (`/c/:name`): header with join/leave, post list, compose pre-fills community, mod panel link for mods

---

### Phase 8 — Notifications

- Nav badge from `NotificationContext`; dropdown with 5 recent + "View all"
- Inbox page: grouped, typed, clickable (marks read + navigates), "Mark all read"
- Preferences page: per-type toggles for all 14 notification types

---

### Phase 9 — Direct messages (1-on-1 only)

**E2EE implementation (Web Crypto API):**
- Key gen on register: RSA-OAEP 2048-bit; public key -> server via `PATCH /users/me`; private key -> IndexedDB
- Key loading on login: from IndexedDB; if missing (new device), generate fresh + publish; show "previous device messages can't be decrypted" notice
- Encrypt: fetch recipient public key, `crypto.subtle.encrypt`, base64 -> `POST /messages`
- Decrypt: base64-decode ciphertext, `crypto.subtle.decrypt`, UTF-8 decode

**Conversations inbox** (`/messages`): sorted by recency, decrypted snippets, unread dots
**Thread** (`/messages/:username`): decrypt on load, own/their bubble alignment, compose encrypts before send, typing indicator via WS, mark read, live append on `new_message`

---

### Phase 10 — Search

Search bar submits to `/search?q=`. Results page with type filter tabs (All | Posts | Users | Communities). Posts as compact cards, users with follow button, communities with join button.

---

### Phase 11 — Settings

- `/settings/account`: change password, 2FA setup/disable (QR code + backup codes)
- `/settings/profile`: display name, bio, avatar
- `/settings/notifications`: per-type toggles
- `/settings/friend-groups`: CRUD groups + member management
- `/settings/data` (GDPR): data export download, account deletion (password required, 7-day grace, cancel option)

---

### Phase 12 — Moderation panel (`/c/:name/mod`)

Visible to moderator/senior_mod/owner only. Tabs: removed content (restore), active bans, ban proposals (vote), mod promotions (vote). Forms: propose ban (target, reason, CoC violation, permanent/expiry), propose mod promotion (target, role).

---

### Phase 13 — WebSocket event handling

Connect to `WS /ws?token=<jwt>` after login. Reconnect with exponential backoff (1s -> 60s).

| Event | Handler |
|---|---|
| `new_post` | "New posts available" banner on feed |
| `new_comment` | Append to thread if on matching post |
| `new_message` | Increment DM badge; append + decrypt if on thread |
| `karma_update` | Update AuthContext karma |
| `notification` | Increment badge; prepend to dropdown |
| `typing` | Show "typing..." for 3s in DM thread |

On logout: close WS cleanly, clear WSContext.

---

### Phase 14 — PWA configuration

Configure `vite-plugin-pwa`: manifest (standalone, icons 192+512), Workbox (precache shell, network-first API, cache-first static/images), offline fallback page, "Add to home screen" prompt via `beforeinstallprompt`.

---

### Accessibility requirements (non-negotiable)

- All interactive elements keyboard-navigable (Tab order, Enter/Space)
- Meaningful `alt` text on all images; avatar `alt` = `@username`
- WCAG 2.1 AA contrast: 4.5:1 body text, 3:1 large text/UI
- `:focus-visible` outlines never removed
- Icon-only buttons must have `aria-label`
- Error messages use `role="alert"`
- Semantic HTML: `<nav>`, `<main>`, `<article>`, `<section>` — no div soup
- Respect `prefers-reduced-motion`

---

### Implementation priority

| Phase | What | Why first |
|---|---|---|
| 0 | Backend prerequisites (stories, unified feed) | Frontend depends on these |
| 1 | Infrastructure (AuthContext, shell, API modules, shared components) | Everything renders inside it |
| 2 | Auth flows | Blocks users from using the app |
| 3 | Feed + stories + compose | Core content loop |
| 4 | PostCard rewrite | Core content loop |
| 5 | Post detail + comments | Core content loop |
| 6 | User profiles | Social graph |
| 7 | Communities | Content organisation |
| 8 | Notifications | Re-engagement |
| 9 | Search | Discovery |
| 10 | DMs (without E2EE first, add encryption as follow-up) | Communication |
| 11 | Settings + GDPR | Compliance |
| 12 | Moderation panel | Required before launch |
| 13 | WS event handling | Real-time polish |
| 14 | PWA + service worker | Offline + installable |
| 15 | DM E2EE key management | Security hardening |
