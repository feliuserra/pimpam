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
│   │   │   ├── users.py            # profiles, follow/unfollow, block
│   │   │   ├── feed.py             # chronological feed
│   │   │   ├── posts.py            # CRUD + vote + boost + share
│   │   │   ├── comments.py         # nested comments + reactions
│   │   │   ├── communities.py      # CRUD + join/leave
│   │   │   ├── moderation.py       # bans, appeals, mod promotion
│   │   │   ├── admin.py            # site-wide admin (reports, bans, suspensions)
│   │   │   ├── reports.py          # user content reporting
│   │   │   ├── hashtags.py         # trending, lookup, posts-by-tag
│   │   │   ├── issues.py           # community issue tracker
│   │   │   ├── search.py           # Meilisearch full-text + hashtag search
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
│   │   ├── api/                    # Domain API modules (auth, users, posts, etc.)
│   │   ├── contexts/               # AuthContext, NotificationContext, WSContext
│   │   ├── pages/                  # Route pages + settings/
│   │   └── components/             # PostCard, CommentCard, CropModal, ui/, mod/
│   └── vite.config.js              # Dev proxy -> localhost:8000
├── requirements.in                 # Abstract deps (edit this)
├── requirements.txt                # Pinned lockfile (uv-generated)
├── docker-compose.yml              # PostgreSQL, Redis, Meilisearch
└── CLAUDE.md
```

---

## Current Status

**590 tests.** Backend is complete. Frontend is substantially complete — all major pages and components implemented.

**Backend — implemented:**
- Auth: register, login, refresh (bcrypt + JWT, rate-limited)
- 2FA (TOTP): setup, verify, disable; AES-encrypted secrets at rest
- Password reset: link mode (15 min) or code mode (6-digit, 10 min); rate-limited 3/hour
- Logout + change password (both bump `token_version` to revoke all refresh tokens)
- Email verification: token emailed on register (60-min, single-use, SHA-256 stored); unverified accounts auto-deleted after 30 days
- Account deletion: 7-day grace period with cancel option; hourly task executes (posts/comments anonymised, messages deleted, user hard-deleted)
- GDPR: data export endpoint; consent log at registration; 30-day consent purge
- User profiles: follower/following counts, `is_following` flag, cover image, accent color, location/website/pronouns, pinned post, draggable layout sections, community stats toggle
- Unified chronological feed (followed users + joined communities, cursor-paginated)
- Stories: ephemeral posts with configurable duration; no seen-by tracking; hourly cleanup
- Posts: create, edit (1h window), delete, vote, karma, boost (AP Announce), share
- Comments: nested (5 levels), sort latest/top, reactions (agree/love/misleading/disagree) with `user_reaction` in responses, mod remove/restore
- Communities: create, list, join/leave; two-tier karma (global + per-community); auto role promotion at 50 community karma; audit log
- Moderation: role hierarchy (member -> trusted_member -> moderator -> senior_mod -> owner); ban proposals (10-vote consensus), appeals, mod promotion, ownership transfer
- Follow/unfollow (local + federated, pending state)
- Direct messages: E2EE ciphertext only, inbox, conversation thread, mark as read
- Friend groups with group-scoped post visibility
- Rate limiting on all write endpoints and feed
- Media uploads: JPEG/PNG/WebP/GIF -> WebP, EXIF strip, resize, S3 storage; cover image type supported
- Search: full-text via Meilisearch (posts, users, communities, hashtags)
- Hashtags: auto-extracted from post title+content, trending, per-hashtag post listing, search integration
- User blocking: block/unblock users, blocked users hidden from feeds/search/suggestions
- Content reporting: report posts, comments, stories (rate-limited, one report per content per user)
- Admin layer: report management (resolve/dismiss), global bans/unbans, user suspensions, content removals
- Issue tracker: community-submitted bugs/features/improvements, voting, comments, admin status updates, security flag
- Device tokens: APNs/FCM token registration for push notifications (iOS/Android/Web)
- ActivityPub federation: WebFinger, NodeInfo, Actor, Inbox, Outbox, HTTP Signatures
- WebSocket real-time: new_post, new_comment, new_message, karma_update, notifications via Redis pub/sub; typing indicators
- Notifications: 14 event types, grouped, per-type opt-out, real-time WS push
- Multi-image posts (behind `MULTI_IMAGE_POSTS_ENABLED` flag)

**Frontend — implemented:**
- App shell: bottom tab bar (mobile) + left sidebar (desktop), per-tab headers, AuthContext, NotificationContext, WSContext
- Auth flows: login, register (with GDPR consent), TOTP 2FA, email verification banner, forgot/reset password, logout
- Feed: chronological post stream, compose modal, stories row (compose, viewer)
- PostCard: author, community badge, votes (optimistic UI), comments, boost, share, hashtag pills, images, overflow menu
- Post detail: full content, image gallery + lightbox, comment thread (nested, reactions), inline reply
- User profiles: inline editing (cover, avatar with crop modal, bio fields, accent color, pinned post, layout reorder, community stats toggle)
- Communities: your communities, discover, create modal, community page with post list, mod panel
- Notifications: badge, grouped inbox, mark all read, per-type preferences
- Messages: conversation inbox, message thread, new DM modal, message bubbles
- Search: full-text search with tabs (All, Posts, Users, Communities, Hashtags), trending hashtags
- Hashtag pages: hashtag detail with tagged posts, infinite scroll
- Settings: account (password, 2FA), profile, notifications, friend groups, data (GDPR export, account deletion)
- Moderation panel: removed content, bans, ban proposals, mod promotions, ownership transfer
- Issues tracker: submit, vote, comment, admin management
- Shared UI: Avatar, Button, Modal, Toast, Spinner, Skeleton, ErrorBoundary, RelativeTime, CropModal
- PWA: service worker, offline fallback, update prompt
- Legal pages: Privacy, Terms
- Discovery page

**Not yet implemented:**
- Multiple images per post UI
- NCMEC content hash-matching
- BYOS (user-provisioned storage)
- Karma privilege thresholds beyond mod eligibility
- Mod rewards / separate moderation karma track
- DM E2EE key management (Web Crypto API)

---

## Planned Improvements

1. ~~**Fix comment listing N+1**~~ DONE — batch queries, 3 DB round-trips regardless of page size.
2. ~~**Rate limit comment creation**~~ DONE — `1/30 seconds` per user.
3. ~~**Expand search**~~ DONE — users + communities + hashtags indexes added.
4. ~~**Admin layer**~~ DONE — site-wide admin flag, global bans, user suspension, content removal, report management.

---

## Frontend Roadmap

All major phases are complete. The frontend is a fully functional React + Vite PWA.

### Completed phases

| Phase | Status |
|---|---|
| 0 — Backend prerequisites (stories, unified feed) | DONE |
| 1 — Infrastructure (shell, contexts, API modules, shared UI) | DONE |
| 2 — Auth flows (register, login, 2FA, email verify, password reset) | DONE |
| 3 — Feed + stories + compose | DONE |
| 4 — PostCard (votes, comments, boost, share, hashtags, images) | DONE |
| 5 — Post detail + comments (gallery, lightbox, nested reactions) | DONE |
| 6 — User profiles (inline edit, cover, avatar crop, accent color, pinned post, layout reorder) | DONE |
| 7 — Communities (discover, create, community page, mod panel link) | DONE |
| 8 — Notifications (badge, inbox, mark all read, per-type prefs) | DONE |
| 9 — Search (posts, users, communities, hashtags, trending) | DONE |
| 10 — DMs (inbox, thread, new DM modal, message bubbles) | DONE (without E2EE) |
| 11 — Settings (account, profile, notifications, friend groups, GDPR) | DONE |
| 12 — Moderation panel (removed content, bans, proposals, promotions) | DONE |
| 13 — WS event handling | DONE |
| 14 — PWA (service worker, offline, update prompt) | DONE |

### Remaining

| Phase | What |
|---|---|
| 15 | DM E2EE key management (Web Crypto API — RSA-OAEP, IndexedDB for private key) |

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
