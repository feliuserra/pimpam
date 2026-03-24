# CLAUDE.md — PimPam Development Guide

This file guides Claude Code when working on PimPam, an open-source, ad-free, human-first social network.

---

## Project Overview

**The hypothesis:** Social networks are harmful because of how they're built and who they're built for — not because social connection itself is harmful. We're removing the specific structural incentives that cause most of the damage — algorithmic amplification, surveillance capitalism, centralised control — and seeing what grows in their place.

PimPam is a community-owned social platform built as an ethical alternative to corporate social media. It has no algorithmic feeds, no ads, no data exploitation, and is governed by its community.

**Core features to build:**
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
| Database | PostgreSQL |
| ORM | SQLAlchemy 2.0 (async) |
| Migrations | Alembic |
| Federation | ActivityPub (HTTP Signatures, WebFinger) |
| Real-time | WebSockets via FastAPI |
| Password hashing | bcrypt via passlib (cost 12) |
| RSA signing | cryptography (per-user key pair for AP) |
| JWT tokens | python-jose |
| Rate limiting | slowapi |
| HTTP client | httpx (federation delivery) |
| Encryption in transit | TLS 1.3 |
| Encryption at rest | AES-256 |
| DM encryption | End-to-end (client-side keys) |
| Frontend linting | ESLint + Prettier |
| Backend linting | Ruff + Black |

---

## Development Setup

### Install uv (once, globally)

[uv](https://github.com/astral-sh/uv) is the package manager for this project. Install it once on your machine:

```bash
curl -Ls https://astral.sh/uv/install.sh | sh
```

uv replaces `pip`, `venv`, and `pip-tools` in a single fast tool.

---

### Backend (FastAPI)

```bash
# 1. Clone
git clone https://github.com/feliuserra/pimpam.git
cd pimpam

# 2. Create a virtual environment and activate it
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Install backend dependencies from the lockfile
uv pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your local DB credentials and secrets

# 5. Run database migrations
alembic upgrade head

# 6. Start the API server
uvicorn app.main:app --reload

# API docs available at http://localhost:8000/docs (Swagger UI)
# and http://localhost:8000/redoc (ReDoc)
```

### Frontend (React)

```bash
cd client
npm install
npm run dev
```

### Tests & Linting

```bash
# Backend
pytest
ruff check .
black --check .

# Frontend
npm test
npm run lint
```

### Docs (Sphinx)

```bash
cd docs
sphinx-build -b html . _build/html
open _build/html/index.html  # macOS
```

Docs source lives in ``docs/``. The ``missing.rst`` file tracks all unimplemented features — update it as things get built.

---

### Managing dependencies

Never edit `requirements.txt` by hand. The workflow is:

```bash
# 1. Add or change a package in requirements.in
# 2. Regenerate the lockfile
uv pip compile requirements.in -o requirements.txt

# 3. Install the updated lockfile
uv pip install -r requirements.txt

# 4. Commit both files
git add requirements.in requirements.txt
```

PostgreSQL must be running locally. Database setup instructions will live in `docs/setup.md` as the schema is defined.

---

## Architecture Principles

These are non-negotiable — they define what PimPam is:

1. **No algorithmic ranking.** Feeds are always chronological. Never reorder content by engagement metrics.
2. **No ads, no tracking, no behavioral analytics.** Collect only the minimum data needed.
3. **Privacy by design.** Direct messages are E2E encrypted. The server stores only ciphertext.
4. **AGPL-3.0.** Never introduce dependencies that would conflict with this license.
5. **Accessibility over performance tricks.** Prefer clear, accessible code over clever optimizations.
6. **Simplicity first.** Don't over-engineer. Build the minimum that works correctly and securely.

---

## Security Requirements

All code touching security-sensitive areas must follow these rules. Two maintainer reviews are required for security-sensitive changes.

### Authentication
- Hash passwords with bcrypt via `passlib[bcrypt]` (minimum cost factor 12)
- Use JWT short-lived access tokens + refresh tokens; support rotation
- Implement rate limiting on auth endpoints via `slowapi` (login, register, password reset)
- Support 2FA (TOTP) — do not make it optional to implement later

### Encryption
- All connections: TLS 1.3 minimum
- All data at rest: AES-256
- Direct messages: E2E encrypted client-side; the server must never hold plaintext message content

### Input Validation & Injection Prevention
- Use SQLAlchemy ORM or parameterized queries for all DB interactions — never string-concatenate SQL
- Use Pydantic models for all request validation — FastAPI enforces this at the route level
- Set Content Security Policy (CSP) headers via middleware
- Validate and sanitize all file uploads (type, size, content)
- Never trust user input server-side

### Least Privilege
- Database users should only have the permissions they need
- Services should not run as root
- Secrets must never be hardcoded — use environment variables

### Dependency Management
- Scan dependencies for vulnerabilities before adding them (`npm audit`)
- Keep dependencies minimal and auditable

### Vulnerability Reporting
- Security issues go to `security@pimpam.org` (do not open public GitHub issues)
- Expected response: 48 hours acknowledgment, 7 days assessment

---

## Data Protection (GDPR)

- Collect only minimum necessary data
- Never sell, share, or repurpose user data
- Retain technical logs for a maximum of 30 days
- Do NOT collect: location data, device fingerprints, browsing history, contact lists, biometric data, behavioral analytics
- Users must be able to: access, correct, delete, export, restrict, and object to their data

---

## Code Standards

### Style
- **Backend**: follow Ruff and Black config; run `ruff check . && black --check .` before every commit
- **Frontend**: follow ESLint and Prettier config; run `npm run lint` before every commit
- Write clear code over clever code; prefer readability and maintainability
- Use Python type hints everywhere in the backend — FastAPI depends on them for validation and docs

### API Design
- The FastAPI backend is the **single source of truth** — all features are exposed as API endpoints first
- Use Pydantic schemas for all request and response bodies; never return raw ORM objects
- Version the API from the start: prefix all routes with `/api/v1/`
- Document every endpoint with a docstring — FastAPI renders these in Swagger UI automatically
- Use async route handlers (`async def`) to take advantage of FastAPI's async capabilities

### Testing
- **Backend**: use `pytest` with `httpx.AsyncClient` for API tests; test against a real test database, not mocks
- **Frontend**: add tests for every new component or behavior
- Add tests that would catch any bug being fixed
- Aim for meaningful coverage, not 100% line coverage

### Pull Requests
- One feature or fix per PR — keep them focused
- Branch naming: `feature/description`, `fix/description`, `docs/description`
- Write a clear PR description: what, why, and how
- All PRs require at least one maintainer review
- Security-sensitive PRs require two maintainer reviews

### Review Checklist
Before submitting or approving code, verify:
- [ ] Does it work correctly?
- [ ] Is it secure? (see Security Requirements above)
- [ ] Is it accessible?
- [ ] Is it maintainable?
- [ ] Does it respect user privacy?
- [ ] Is it consistent with the rest of the codebase?
- [ ] Does it include tests?
- [ ] Do `ruff`, `black`, and `npm run lint` pass?

---

## Code of Conduct (Summary for Claude)

PimPam enforces a welcoming, harassment-free environment. When generating code, comments, documentation, or commit messages:

- Use inclusive, respectful language
- Do not produce content that demeans, excludes, or harms any group
- Do not generate code that harvests user data beyond stated purposes
- Prioritize accessibility — screen reader compatibility, keyboard navigation, color contrast
- Violations are reported to `conduct@pimpam.org`

The full Code of Conduct is in `CODE_OF_CONDUCT.md`.

---

## Decision-Making

- Day-to-day: maintainers decide
- Larger features: open a GitHub Discussion for community input before implementing
- Changes to core principles (no ads, no algorithms, AGPL license): require broad community consensus — do not make these changes unilaterally

---

## What NOT to Build

These are explicitly out of scope and contrary to PimPam's values:

- Algorithmic content ranking or recommendation engines
- Ad serving or targeting infrastructure
- Behavioral analytics or user profiling
- Any feature that monetizes user data
- Any proprietary components (must stay AGPL-compatible)
- Shadow banning or opaque moderation (all moderation must be transparent and appealable)

---

## Design Language & UX

These decisions are locked in. All frontend work must follow them.

### Navigation model

```
Mobile — fixed bottom tab bar (5 tabs):
  [Feed]  [Communities]  [Messages]  [Notifications]  [Profile]

Desktop (≥ 1024px) — left sidebar with the same 5 items as vertical nav links.
No bottom bar on desktop. Content area fills the remaining width.
```

Each tab has a thin header bar above its content area:

| Tab | Left | Right |
|---|---|---|
| Feed | PimPam logo | 🔍 search icon + ✏️ compose button |
| Communities | "Communities" | 🔍 search pill ("Search communities…") |
| Messages | "Messages" | ✏️ compose new DM icon |
| Notifications | "Notifications" | ✓ mark-all-read icon |
| Profile | `@username` | ⚙️ settings gear |

**Badges:** unread DM count on Messages tab; unread notification count on Notifications tab.

---

### Stories

Real ephemeral stories. These constraints keep them consistent with PimPam's values:

- **No "seen by" list.** Viewing a story is never recorded or surfaced to the author. Zero behavioural tracking.
- **No countdown timer.** Stories disappear when they expire. No urgency UI.
- **User-configurable duration.** Default 24 h; author picks 12 h / 24 h / 48 h / 7 days at post time.
- **Image + optional caption** (max 200 chars). No video in v1.
- **Moderation grace period.** Reported stories are soft-deleted (hidden from viewers immediately) but the row is retained for 48 h so moderators can review before permanent deletion.

Stories row in the Feed tab — horizontal scroll of circular avatars. A coloured ring = unseen story. Your own avatar shows a `+` to compose. Tapping a ring opens a full-screen story viewer (swipe left/right to navigate between stories from the same user).

---

### Feed content

The feed is a single unified chronological stream combining:
1. Posts by users the viewer follows
2. Posts in communities the viewer has joined

A post that matches both (a followed user posts to a joined community) appears only once.

---

### Search

- **Feed tab:** magnifying glass icon in the header. Tapping slides a full-width input bar down with a smooth animation. Shows recent searches below. Escape or tap-outside collapses it.
- **Communities tab:** a tappable pill ("Search communities…") rather than a bare icon — finding communities is a primary action, so the affordance is more prominent. Same expand behaviour.

---

### Communities tab layout

```
┌──────────────────────────────────────┐
│ Communities       [Search communities…]│
├──────────────────────────────────────┤
│ Your communities                     │
│ [c/design] [c/music] [c/tech]  →    │  ← horizontal scroll
├──────────────────────────────────────┤
│ Discover          [Popular] [New]    │
│  c/philosophy   1.2k members   [+]  │
│  c/cooking        890 members  [+]  │
└──────────────────────────────────────┘
```

---

### Aesthetic direction

- **Mobile-first.** Desktop adapts via sidebar, not a different layout.
- **Familiar over novel.** Borrow proven patterns: Instagram (stories row, profile layout, tab navigation), Reddit (community pages, upvote/downvote), WhatsApp/iMessage (message threads). Do not invent new patterns when a well-understood one exists.
- **Minimal chrome.** Content is the UI. Keep headers, footers, and chrome as thin as possible.
- **No dark patterns.** No countdown timers, no seen-by lists, no auto-playing video, no read-receipt pressure, no engagement-bait mechanics beyond a clean chronological scroll.
- **Neutral palette + one accent colour.** Let user-generated content provide visual variety. The accent colour is used for interactive elements (buttons, active tab indicator, story ring).
- **Direct messages are 1-on-1 only** in v1. No group chats.

---

## File Layout

```
pimpam/
├── app/
│   ├── main.py                     # App entry point — registers all routers
│   ├── api/
│   │   ├── v1/                     # Versioned REST API (/api/v1/*)
│   │   │   ├── auth.py             # POST /auth/register, /login, /refresh, /totp/*
│   │   │   ├── users.py            # GET|PATCH /users/me, follow/unfollow
│   │   │   ├── feed.py             # GET /feed (chronological, cursor-paginated)
│   │   │   ├── posts.py            # CRUD /posts + vote + boost + share
│   │   │   ├── comments.py         # /posts/{id}/comments + /comments/{id}/* (reactions, replies)
│   │   │   ├── communities.py      # CRUD /communities + join/leave + member karma
│   │   │   ├── moderation.py       # Bans, appeals, mod promotion, ownership transfer, comment mod
│   │   │   ├── search.py           # GET /search (Meilisearch full-text)
│   │   │   └── messages.py         # E2EE /messages
│   │   ├── ws.py                   # WS /ws?token=<jwt> — real-time events
│   │   └── federation/             # ActivityPub endpoints (root-level paths)
│   │       ├── wellknown.py        # /.well-known/webfinger, /nodeinfo/2.1
│   │       └── actor_routes.py     # /users/{u}/inbox|outbox|followers|following
│   ├── federation/                 # AP protocol logic (not routes)
│   │   ├── constants.py            # AP context URLs, content types
│   │   ├── crypto.py               # RSA keygen, HTTP Signature sign/verify
│   │   ├── actor.py                # Build Actor, Note, Create, Accept dicts
│   │   ├── signatures.py           # FastAPI dependency: verify inbox signature
│   │   ├── fetcher.py              # Fetch + TTL-cache remote actor documents
│   │   ├── delivery.py             # POST activities to remote inboxes
│   │   └── activity_handler.py     # Dispatch Follow/Undo/Create/Delete
│   ├── models/                     # SQLAlchemy ORM models
│   │   ├── user.py                 # User (local + remote stubs, RSA keys)
│   │   ├── post.py                 # Post (ap_id for federated content)
│   │   ├── community.py            # Community + CommunityMember
│   │   ├── message.py              # E2EE Message (ciphertext only)
│   │   ├── follow.py               # Follow (local and federated)
│   │   └── remote_actor.py         # RemoteActor cache (public keys, TTL)
│   ├── schemas/                    # Pydantic request/response models
│   │   ├── user.py
│   │   ├── post.py
│   │   ├── community.py
│   │   ├── message.py
│   │   ├── token.py
│   │   └── federation.py           # RemoteActorCreate/Read
│   ├── crud/                       # DB queries — keep routes thin
│   │   ├── user.py
│   │   ├── post.py
│   │   ├── community.py
│   │   └── remote_actor.py
│   ├── core/
│   │   ├── config.py               # All settings via pydantic-settings + .env
│   │   ├── security.py             # JWT create/decode, bcrypt hash/verify
│   │   └── dependencies.py         # DBSession, CurrentUser FastAPI deps
│   └── db/
│       ├── base_class.py           # SQLAlchemy DeclarativeBase
│       ├── base.py                 # Imports all models (used by Alembic)
│       └── session.py              # Async engine + session factory
├── alembic/
│   ├── env.py                      # Async-aware Alembic config
│   ├── script.py.mako
│   └── versions/                   # Generated migration files go here
├── tests/
│   └── conftest.py                 # pytest fixtures (SQLite in-memory)
├── client/                         # React PWA frontend
│   ├── src/
│   │   ├── api/client.js           # Axios instance with token refresh
│   │   ├── pages/                  # Feed, Login, Register
│   │   └── components/             # PostCard, ...
│   └── vite.config.js              # Dev proxy: /api → localhost:8000
├── requirements.in                 # Abstract deps (edit this)
├── requirements.txt                # Pinned lockfile (generated by uv)
├── docker-compose.yml              # PostgreSQL, Redis, Meilisearch
├── alembic.ini
├── .env.example
└── CLAUDE.md
```

---

## Current Status

The backend is complete. **399 tests, 88% coverage** (`pytest -n auto`). The frontend is the remaining work — see the Frontend Roadmap below.

**Implemented:**
- Auth: register, login, refresh (bcrypt + JWT, rate-limited)
- 2FA (TOTP): setup, verify, disable; second login step; secrets AES-encrypted at rest
- Password reset: link mode (15 min, URL token) or code mode (6-digit, 10 min); client chooses via `mode` field; SMTP delivery (no-op in dev); rate-limited 3/hour per account; resets increment `User.token_version` to revoke all refresh tokens; 404 for unknown email (deliberate)
- Logout: `POST /auth/logout` — bumps `token_version`, invalidating all refresh tokens; returns 204
- Change password: `POST /auth/change-password` — requires current password; bumps `token_version` (forces re-login everywhere); returns 200
- Email verification: token emailed on register (60-min expiry, single-use, SHA-256 hash stored); `GET /auth/verify?token=` to activate; `POST /auth/resend-verification` for new token; `CurrentUser` dep returns 403 `email_not_verified` if unverified; unverified accounts auto-deleted after 30 days by hourly background task
- Account deletion: `POST /users/me/delete` schedules hard-delete with 7-day grace period (password required); `DELETE /users/me` alias; `POST /users/me/delete/cancel` cancels; hourly task executes due deletions — posts/comments anonymised, received messages deleted, user row hard-deleted
- GDPR compliance: `GET /users/me/data-export` returns full personal data archive; consent log recorded at registration (ToS, Privacy Policy, Age confirmation); consent records purged after 30 days by hourly task
- User profiles: `GET /users/me`, `GET /users/:username` with `follower_count`, `following_count`, `is_following`; `GET /users/:username/followers`, `/following`, `/posts`
- Unified chronological feed — posts from followed users **and** joined communities, cursor-paginated, no ranking, no algorithms
- Stories: ephemeral image + caption posts; user-configurable duration (12h/24h/48h/7d, default 24h); no seen-by tracking; no expiry timestamp in API responses; `POST /stories`, `GET /stories/feed`, `DELETE /stories/:id`, `POST /stories/:id/report`; hourly cleanup of expired stories
- Posts: create, edit (1-hour window), delete, vote (+1/-1), karma propagation, boost (AP Announce), share (reshare to followers/community)
- Comments: create (up to 5 levels nesting), list (sort: latest/top), replies, author soft-delete, reactions (agree/love/misleading/disagree), mod remove/restore
- Comment reactions: agree (+1 karma), love (+2), misleading (−2), disagree (0, activates on reply, 10/day limit)
- Communities: create, list (sort: popular/alphabetical/newest), join/leave, post listing
- Two-tier karma: global (`User.karma`) + per-community (`CommunityKarma`) with automatic role promotion at 50 community karma
- Moderation role hierarchy: member → trusted_member → moderator → senior_mod → owner
- Moderation: remove/restore posts and comments, ban proposals (10-vote consensus), ban appeals (10-vote overturn, 1-week cooldown, original voters excluded), mod promotion (karma-gated, majority vote), ownership transfer (accept/reject flow)
- Follow/unfollow (local and federated users, with pending state)
- Direct messages: send (E2EE ciphertext only), inbox, conversation thread, mark as read
- Friend groups: create/manage private groups; posts can be scoped to a specific group (`visibility=group`)
- Rate limiting on all write endpoints and feed
- Media uploads: JPEG/PNG/WebP/GIF → WebP, EXIF strip, resize, S3-compatible storage
- Search: full-text via Meilisearch over posts, users, and communities; `?type=post|user|community` filter
- ActivityPub federation: WebFinger, NodeInfo, Actor, Inbox, Outbox, HTTP Signatures; outgoing delivery gated by `FEDERATION_ENABLED`
- WebSocket real-time updates: `WS /ws?token=<jwt>` — new_post, new_comment, new_message, karma_update, notification events via Redis pub/sub; typing indicators
- Notifications: persistent inbox, 14 event types, grouped reactions/votes/new_comments, per-type opt-out preferences, real-time WS push + stored
- Multi-image posts: `PostImage` table; `MULTI_IMAGE_POSTS_ENABLED` flag (default false, max 1 image; up to 10 when enabled)

**Not yet implemented:**
- React frontend (client/ skeleton only — see Frontend Roadmap and Design Language sections below)
- Multiple images per post UI (`MULTI_IMAGE_POSTS_ENABLED=true` to activate backend support)
- NCMEC content hash-matching (post-upload async check)
- BYOS (user-provisioned storage)
- Karma privilege thresholds beyond mod eligibility
- Admin layer (site-wide moderation, global bans — required before public launch)
- Mod rewards / separate moderation karma track

---

## Planned Improvements

These are known issues to address in upcoming work, in priority order:

1. ~~**Fix comment listing N+1**~~ ✅ — replaced per-comment reaction/reply queries with two batch queries (`get_reaction_counts_batch`, `get_reply_counts_batch`). Full page now lands in 3 DB round-trips regardless of page size.

2. ~~**Rate limit comment creation**~~ ✅ — `POST /posts/{id}/comments` limited to `1/30 seconds` per user.

3. ~~**Expand search**~~ ✅ — `users` and `communities` Meilisearch indexes added alongside `posts`. `GET /api/v1/search` now accepts `?type=post|user|community` (default: all three). Indexing wired into register, profile update, and community create.

4. **Admin layer** — Platform-level moderation separate from community roles: site-wide admin flag on `User`, global bans, user suspension, platform content removal, admin-only endpoints. Required before any public launch.

---

## Verifying the Backend

### 1. First-time setup

```bash
# Start PostgreSQL (and Redis, Meilisearch) via Docker
docker compose up -d

# Create and activate the Python virtual environment
uv venv
source .venv/bin/activate

# Generate the pinned lockfile (requirements.txt doesn't exist yet — do this once)
uv pip compile requirements.in -o requirements.txt

# Install all dependencies
uv pip install -r requirements.txt

# Copy and configure environment variables
cp .env.example .env
# Open .env and set SECRET_KEY to a random string:
# python -c "import secrets; print(secrets.token_hex(32))"

# Generate and apply the initial database migration
alembic revision --autogenerate -m "initial schema"
alembic upgrade head

# Start the API
uvicorn app.main:app --reload
```

### 2. Smoke tests (run while the server is up)

**Health check:**
```bash
curl http://localhost:8000/health
# → {"status":"ok","version":"0.1.0","federation":true}
```

**Register a user:**
```bash
curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","email":"alice@example.com","password":"supersecret"}' | python -m json.tool
```

**Log in and capture the token:**
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"supersecret"}' | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

**Fetch your own profile:**
```bash
curl -s http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

**Check the AP actor endpoint (federation):**
```bash
curl -s http://localhost:8000/users/alice \
  -H "Accept: application/activity+json" | python -m json.tool
# → Should return the ActivityPub Actor document with publicKey
```

**Check WebFinger (set DOMAIN=localhost:8000 in .env first):**
```bash
curl -s "http://localhost:8000/.well-known/webfinger?resource=acct:alice@localhost:8000" | python -m json.tool
```

**Interactive API docs:**
Open [http://localhost:8000/docs](http://localhost:8000/docs) in your browser.

### 3. Run the test suite

```bash
pytest -v
```

Tests use an in-memory SQLite database — no PostgreSQL needed for testing.

---

## Frontend Roadmap

The backend is complete (381 tests, 88% coverage). The `client/` directory is a React + Vite PWA skeleton. This section is the authoritative checklist for all frontend work.

### What already exists (working)

| File | State |
|---|---|
| `src/api/client.js` | Complete — Axios + Bearer token attach + silent refresh interceptor |
| `src/App.jsx` | Skeleton — 3 routes only, no nav shell |
| `src/pages/Login.jsx` | Complete — functional form |
| `src/pages/Register.jsx` | Mostly complete — missing GDPR consent checkboxes |
| `src/pages/Feed.jsx` | Functional — missing compose button and post actions |
| `src/components/PostCard.jsx` | Skeleton — no author, no votes, no comments |

---

### Phase 0 — Backend prerequisites (complete before any frontend work)

Two backend additions are required before the frontend can be built.

**0a. Stories backend**

- `app/models/story.py` — new `Story` model: `id`, `author_id` (FK → users, CASCADE), `image_url`, `caption` (nullable, String 200), `expires_at` (DateTime, indexed), `is_removed` (bool, default false), `created_at`
- `app/db/base.py` — import Story so Alembic picks it up
- `app/api/v1/stories.py` — new router, 4 endpoints:
  - `POST /stories` — create story (auth required; `image_url` from prior `/media/upload`, optional `caption`, `duration_hours` default 24, max 168)
  - `GET /stories/feed` — stories from followed users + joined communities, not expired, `created_at` desc; returns `author_username`, `author_avatar_url`, `story_id`, `image_url`, `caption`, `created_at` — **no `expires_at` in response** (prevents countdown UI)
  - `DELETE /stories/:id` — own story early deletion (author only, 204)
  - `POST /stories/:id/report` — soft-deletes the story (`is_removed = true`), retains row 48 h for mod review (204)
- `app/main.py` — register stories router; add to hourly cleanup: `DELETE FROM stories WHERE expires_at < now() AND is_removed = false`
- Alembic migration: `alembic revision --autogenerate -m "add stories table"`
- `tests/test_stories.py` — new test file covering: create story, feed includes it, expires_at calculated correctly, early delete works, report soft-deletes, non-author cannot delete, expired stories excluded from feed

**0b. Unified feed query**

Update `GET /feed` to return posts from **followed users + joined communities**, deduplicated, ordered by `created_at` desc, cursor-paginated.

- `app/api/v1/feed.py` or `app/crud/post.py` — extend feed query:
  ```python
  # author_ids from follows WHERE follower_id = me AND is_pending = false
  # community_ids from community_members WHERE user_id = me
  # SELECT posts WHERE (author_id IN author_ids OR community_id IN community_ids)
  #   AND is_removed = false AND visibility = 'public'
  #   ORDER BY created_at DESC LIMIT limit
  # cursor: WHERE created_at < before_timestamp (existing pattern)
  ```
  A post matching both conditions appears once (SQL deduplication via the OR condition, not UNION).
- `tests/test_feed.py` — add: joined-community posts appear in feed; followed-user post to joined community appears only once

---

### Phase 1 — Infrastructure (do first; everything else depends on this)

**App shell & routing**
- **Bottom tab bar** (mobile): 5 tabs — Feed, Communities, Messages, Notifications, Profile. Fixed at the bottom of the viewport. Active tab highlighted with accent colour. Badge counts on Messages and Notifications tabs.
- **Left sidebar** (desktop, ≥ 1024px): same 5 items as vertical nav links. No bottom bar. Content fills remaining width. `useMediaQuery` or a CSS breakpoint controls which layout renders.
- Each tab's content area has its own thin header bar (see Design Language section above for per-tab header contents).
- Expand `App.jsx` with all routes; add `React.lazy` + `<Suspense>` for route-level code splitting.
- `PrivateRoute` already exists but auth state must move from scattered `localStorage.getItem` checks into `AuthContext`.

**State management (React Context)**
- `AuthContext` — current user object, tokens, `login()`, `logout()`; on mount calls `GET /users/me` to hydrate user; on 401 after refresh failure clears context and redirects to `/login`
- `NotificationContext` — unread notification count + unread DM count; both updated by WebSocket events; drives tab badges
- `WSContext` — single WebSocket connection to `WS /ws?token=<jwt>`; established after login, torn down on logout; dispatches typed events to subscribers

**Split `api/client.js` into domain modules**
- `api/auth.js` — login, register, refresh, logout, changePassword, requestPasswordReset, confirmPasswordReset, verifyEmail, resendVerification
- `api/users.js` — getMe, updateMe, getUser, follow, unfollow, getFollowers, getFollowing, getUserPosts, exportData, deleteAccount, cancelDeletion
- `api/posts.js` — getFeed, getPost, createPost, editPost, deletePost, vote, boost, share, uploadImage
- `api/comments.js` — getComments, createComment, deleteComment, react
- `api/communities.js` — list, get, create, join, leave, getPosts
- `api/moderation.js` — removePost, restorePost, removeComment, restoreComment, proposeBan, voteBan, listBans, proposeAppeal, voteAppeal, proposeMod, voteMod
- `api/messages.js` — getConversations, getThread, sendMessage, markRead
- `api/notifications.js` — list, markRead, markAllRead, getPreferences, updatePreferences
- `api/search.js` — search
- `api/friendGroups.js` — list, create, update, delete, addMember, removeMember

**Shared UI components** (build once, use everywhere)
- `Avatar` — `src`, `username`, `size` props; falls back to initials if no avatar URL
- `Button` — variants: primary, secondary, ghost, danger; handles `loading` prop (shows spinner, disables clicks)
- `Modal` — accessible dialog with backdrop, focus trap, Escape to close; used for confirm-delete, compose forms, image viewer
- `Toast` — success/error/info banners, top-right, auto-dismiss after 4 s; exposed via a `useToast()` hook
- `Spinner` / `Skeleton` — loading placeholders for cards and lists
- `ErrorBoundary` — catches render crashes, shows "Something went wrong" fallback
- `InfiniteList` — wraps cursor-paginated lists; uses `IntersectionObserver` to fire "load more" when the bottom sentinel scrolls into view
- `RelativeTime` — formats `created_at` as "3 minutes ago", updates every minute

---

### Phase 2 — Auth flows

**Register page** (extend existing `Register.jsx`)
- Add three required checkboxes before the submit button:
  - "I agree to the Terms of Service"
  - "I agree to the Privacy Policy"
  - "I confirm I am 13 years of age or older"
- Block submit until all three are checked (these map to the `terms_of_service`, `privacy_policy`, `age_confirmation` consent log entries the backend records at registration)
- After successful register: show a "Check your email to verify your account" interstitial instead of auto-navigating to feed (the backend returns `403 email_not_verified` on any authenticated request until the token is clicked)

**Email verification**
- `/verify-email?token=<token>` page — on mount calls `GET /auth/verify?token=`; shows success message or expired-token error with a "Resend verification email" button (`POST /auth/resend-verification`)
- If a logged-in user receives `403 { detail: "email_not_verified" }`, show a persistent top banner: "Please verify your email address. [Resend email]"

**TOTP 2FA login step**
- After `POST /auth/login`, if response body contains `requires_totp: true` and `totp_user_id` (instead of tokens), redirect to `/login/totp`
- `/login/totp` — 6-digit code input; on submit calls `POST /auth/totp/verify` with `{ user_id, code }`; stores tokens and navigates to feed on success

**Password reset**
- `/forgot-password` — email input; calls `POST /auth/password-reset/request` with `{ email, mode: "link" }`; always shows "If that email exists, you'll receive a reset link" (backend always returns 200 regardless)
- `/reset-password?token=<token>` — new password + confirm fields; calls `POST /auth/password-reset/confirm` with `{ token, new_password }`

**Logout**
- Calls `POST /auth/logout`, clears `AuthContext`, redirects to `/login`

---

### Phase 3 — Feed & post compose (extend existing)

**Stories row** (top of the Feed tab, above posts)
- Horizontal scroll of circular avatars. A coloured ring around an avatar = that user has an unseen story. Grey ring = seen. No ring = no active story.
- First item is always the viewer's own avatar with a `+` icon. Tapping it opens the story compose flow.
- Story compose: image picker → full-screen preview → caption input (max 200 chars, optional) → duration selector (12 h / 24 h / 48 h / 7 days, default 24 h) → `POST /stories`
- Tapping another user's avatar opens the full-screen story viewer: image fills the screen, caption overlaid at the bottom, author name + relative timestamp at the top, tap left/right to navigate between multiple stories from the same user, swipe down to close.
- No progress bar, no countdown, no seen-by display.
- Data: `GET /stories/feed` on mount; cache result for the session tab (don't re-fetch on every scroll).

**Post feed** (below stories row)
- Feed now includes posts from followed users **and** joined communities — unified chronological stream from `GET /feed` (backend updated in Phase 0).
- Compose post button (floating action button, bottom-right) opens a compose `Modal` with:
  - Title field (required)
  - Content textarea (optional)
  - URL field (optional, for link posts)
  - Community selector: dropdown of joined communities; leave blank for a personal post
  - Visibility selector: Public / Followers only / Friend group (friend group option shows a sub-selector of the user's groups)
  - Image upload: drag-and-drop or file picker; calls `POST /media/upload` with `media_type=post_image`; shows thumbnail previews before submit; respects `MULTI_IMAGE_POSTS_ENABLED`
- When the user follows nobody and has joined no communities, show an onboarding prompt: "Discover communities →" and "Find people to follow →"
- Update `PostCard` — see Phase 4

**WebSocket-driven feed refresh**
- On `new_post` WS event: show a "New posts available" banner at the top of the feed rather than auto-inserting (avoids layout jumps); clicking it prepends the new posts

---

### Phase 4 — PostCard (complete rewrite)

Every post card needs:
- Author avatar + `@username` link → their profile page
- Community badge if `post.community_id` is set, linking to `/c/:community_name`
- Post title linking to `/posts/:id`; external URL indicator (↗) if `post.url` is set
- Post content snippet — truncate at ~3 lines; "read more" expands inline
- Images — if `post.images.length > 0`, show first image; "+N more" badge if there are additional images; clicking opens the post detail
- Vote buttons — ▲ upvote / ▼ downvote with current karma score in between; calls `POST /posts/:id/vote` with `{ value: 1 }` or `{ value: -1 }`; optimistic UI update (revert on error)
- Comment count — links to `/posts/:id#comments`
- Boost button (reshare to AP followers) — `POST /posts/:id/boost`; shows own-author share button instead on own posts
- Relative timestamp via `RelativeTime` component
- Overflow menu (⋯):
  - Own posts: Edit (only within 1-hour window — check `post.can_edit` or compare `created_at + 1h > now`), Delete
  - Mod/senior-mod/owner viewing another user's post: Remove

---

### Phase 5 — Post detail page (`/posts/:id`)

- Full post content (no truncation)
- All images in a gallery; clicking an image opens a lightbox modal
- Same vote, boost, share actions as PostCard
- Edit post (own posts within 1-hour window): pencil icon swaps content area for a textarea; saves with `PATCH /posts/:id`; shows "Edit window closes in X minutes" countdown
- Delete post (own): confirmation modal → `DELETE /posts/:id` → redirect to feed or community page
- Comment thread:
  - Sort toggle: Latest / Top — calls `GET /posts/:id/comments?sort=latest|top`
  - Nested display up to 5 levels deep with visual left-border indentation per level
  - Each comment: author avatar + username, content (`[deleted]` placeholder if `is_removed: true`), relative timestamp, reaction buttons (agree / love / misleading / disagree) with counts, Reply button, delete button (own comments only)
  - Reaction calls `POST /comments/:id/react` with `{ reaction: "agree"|"love"|"misleading"|"disagree" }`
  - Reply form: renders inline under the parent comment, collapses after submit
  - New top-level comment box: fixed at the bottom of the thread (or below the last comment on short threads)
- On `new_comment` WS event while on this page: append the new comment to the thread

---

### Phase 6 — User profile page (`/@:username` or `/u/:username`)

- Header: avatar (large), display name, `@username`, bio, follower count, following count, global karma, member since date
- Follow / Unfollow button using `is_following` field from `GET /users/:username`; hidden on own profile; calls `POST /users/:username/follow` or `DELETE /users/:username/follow`
- Three tabs: Posts | Followers | Following
  - **Posts**: `GET /users/:username/posts` with `InfiniteList` cursor pagination
  - **Followers**: `GET /users/:username/followers`
  - **Following**: `GET /users/:username/following`
- Own profile: "Edit profile" button opens the edit form (or navigates to `/settings/profile`)

**Edit profile** (own profile only)
- Fields: display name, bio, avatar (file picker → `POST /media/upload` with `media_type=avatar`, preview before save)
- Saves with `PATCH /users/me`

---

### Phase 7 — Communities

**Communities tab — dual view**

The tab has two sections separated by a divider:

*Your communities* — a horizontally scrollable row of joined community icons (small circle with community initial or icon). Tapping one navigates to that community's page. At the end of the row, a "+ Create" chip opens the create form.

*Discover* — sort tabs: Popular | New. List of all communities with name, description snippet, member count, and a [+] join button for non-members. Uses `GET /communities?sort=popular|newest`.

Both sections are visible without scrolling on a typical phone screen (joined row is compact, ~80px tall).

**Create community form**
- Accessible from the "+ Create" chip in the joined row, or from a community page
- Fields: name (lowercase slug, no spaces, validated client-side), description
- Calls `POST /communities`

**Community page (`/c/:name`)**
- Header: community name, description, member count, join / leave button; user's current role badge if a member
- Post list via `GET /communities/:name/posts` with `InfiniteList` cursor pagination (same PostCard)
- Compose post button pre-fills this community in the compose modal
- Sidebar (desktop) / collapsible info section (mobile): moderator list, creation date, link to mod panel (visible only to mods)

---

### Phase 8 — Notifications

**Notification bell (nav bar)**
- Unread count badge, updated in real time from `NotificationContext` (fed by WS `notification` events)
- Dropdown on click: 5 most recent notifications with descriptions and links; "Mark all read" button; "View all →" link

**Notification inbox (`/notifications`)**
- Full list, paginated; grouped by type where the backend groups them (reactions, votes, comments)
- Each item: icon for type, human-readable description linking to relevant content, relative timestamp, unread indicator dot
- Clicking an item calls `POST /notifications/:id/read` and navigates to the linked content
- "Mark all as read" button → `POST /notifications/read-all`

**Notification preferences (`/settings/notifications`)**
- Toggle list, one row per notification type (new_comment, reply, mention, vote, reaction, follow, new_message, moderation_action, ban_proposal_vote, appeal_vote, mod_proposal_vote, ownership_transfer, community_post, boost)
- Loads with `GET /users/me/notification-preferences`; saves each toggle change with `PATCH /users/me/notification-preferences`

---

### Phase 9 — Direct messages (1-on-1 only)

Group chats are out of scope for v1. All message threads are between exactly two users.

**Important — E2EE implementation:**
The server stores only ciphertext. The frontend must handle all encryption using the Web Crypto API.

- **Key generation** (on register, after account creation): call `window.crypto.subtle.generateKey({ name: "RSA-OAEP", modulusLength: 2048, publicExponent: new Uint8Array([1,0,1]), hash: "SHA-256" }, true, ["encrypt","decrypt"])`. Export the public key as SPKI → base64 and send it to the server via `PATCH /users/me` (`public_key` field). Store the private key in `IndexedDB` under the user's ID using `window.crypto.subtle.exportKey("jwk", privateKey)`.
- **Key loading** (on login): retrieve private key from `IndexedDB`. If not found (new device), generate a fresh key pair, publish the new public key. Show a notice: "Messages sent to previous devices can't be decrypted on this device."
- **Encrypting a message**: fetch recipient's public key from `GET /users/:username` (`public_key` field); import it with `crypto.subtle.importKey`; encrypt the plaintext with `crypto.subtle.encrypt({ name: "RSA-OAEP" }, recipientPublicKey, plaintextBytes)`; base64-encode and send as `ciphertext` in `POST /messages`.
- **Decrypting a message**: base64-decode the `ciphertext`; call `crypto.subtle.decrypt({ name: "RSA-OAEP" }, ownPrivateKey, ciphertextBytes)`; decode the result as UTF-8.

**Conversations inbox (`/messages`)**
- List of conversations sorted by most recent message; each shows other user's avatar + name, last message decrypted snippet, unread dot, relative timestamp
- `GET /messages/inbox`

**Conversation thread (`/messages/:username`)**
- `GET /messages/conversation/:user_id`; decrypt each message on load
- Message bubbles: own messages right-aligned, theirs left-aligned; timestamp below each
- Compose box at bottom: encrypts input before sending; calls `POST /messages`
- Typing indicator: send `{ "type": "typing", "recipient_id": N }` over WS when user is typing; show "typing…" when a typing event arrives from the other user
- Mark messages as read on view: `POST /messages/:id/read`
- On `new_message` WS event while on this thread: append and decrypt the new message

---

### Phase 10 — Search

**Search bar (nav bar)**
- Submits to `/search?q=<query>` on Enter

**Search results page (`/search`)**
- Type filter tabs: All | Posts | Users | Communities — appends `&type=post|user|community` to `GET /search?q=`
- Results by type:
  - Posts: compact PostCard (no images)
  - Users: avatar + username + bio snippet + follow/unfollow button
  - Communities: name + description snippet + member count + join button

---

### Phase 11 — Settings

**`/settings`** — hub page with links to sub-sections

**`/settings/account`**
- Change password: current password + new password + confirm → `POST /auth/change-password`
- 2FA setup (if disabled): "Enable 2FA" button → `POST /auth/totp/setup` → display QR code image and manual entry key → 6-digit confirmation input → `POST /auth/totp/enable` → show one-time backup codes
- 2FA disable (if enabled): "Disable 2FA" → prompt for current TOTP code → `POST /auth/totp/disable`

**`/settings/profile`**
- Display name, bio, avatar upload (same as edit profile on profile page)

**`/settings/notifications`**
- Per-type preference toggles (see Phase 8)

**`/settings/friend-groups`**
- List of friend groups (name, member count) — `GET /friend-groups`
- Create group: name field → `POST /friend-groups`
- Each group: expand to show member list, add member (username input → `POST /friend-groups/:id/members`), remove member button (`DELETE /friend-groups/:id/members/:user_id`), delete group (`DELETE /friend-groups/:id`)

**`/settings/data`** (GDPR)
- "Export my data" button → `GET /users/me/data-export` → trigger browser file download of the JSON blob (set `Content-Disposition: attachment` is already handled server-side)
- Danger zone: "Delete my account" → modal requiring the user to type their password → `DELETE /users/me` with `{ password }` → show "Your account is scheduled for deletion in 7 days. [Cancel deletion]"; cancel button → `POST /users/me/delete/cancel`

---

### Phase 12 — Moderation panel (`/c/:name/mod`)

Visible only to users whose role in the community is `moderator`, `senior_mod`, or `owner`.

- **Removed content tab**: paginated list of removed posts and comments with "Restore" button each
- **Active bans tab**: `GET /communities/:name/bans`; each row shows banned username, reason, CoC violation, expiry / permanent flag
- **Ban proposals tab**: open proposals with current vote count and status; "Vote" button for eligible `trusted_member`+ users
- **Mod promotion tab**: open proposals; vote buttons for eligible members
- **Propose ban form**: target username, reason (text), CoC violation type (select: spam / harassment / misinformation / hate_speech / other), permanent toggle, optional expiry date
- **Propose mod promotion form**: target username, target role (select: trusted_member / moderator / senior_mod)

---

### Phase 13 — WebSocket event handling (WSContext)

Connect to `WS /ws?token=<access_token>` after login. Reconnect with exponential backoff (1 s, 2 s, 4 s … up to 60 s) on unexpected close.

| Event `type` | Handler |
|---|---|
| `new_post` | Show "New posts available" banner on `/` feed; clicking it prepends the posts |
| `new_comment` | If currently on `/posts/:id` matching the comment's post, append it to the thread |
| `new_message` | Increment DM unread badge in nav; if on the relevant conversation thread, append and decrypt |
| `karma_update` | Update `AuthContext` user's karma count |
| `notification` | Increment notification badge count; prepend to notification dropdown |
| `typing` | In the relevant DM thread, show "typing…" for 3 s |

On logout: close the WebSocket cleanly (send a close frame), clear the `WSContext`.

---

### Phase 14 — PWA configuration

`vite-plugin-pwa` is already in `package.json`. Configure it in `vite.config.js`:

- Set `manifest`: `name: "PimPam"`, `short_name: "PimPam"`, `display: "standalone"`, `theme_color`, `background_color`, icons at 192×192 and 512×512 (PNG)
- Fill in `public/manifest.json` (already skeleton) with the same values
- Configure Workbox: precache the app shell (JS/CSS bundles, index.html); network-first strategy for API calls; cache-first for static assets and uploaded images
- Offline fallback: a cached `/offline` page shown when the network is unavailable and the requested resource isn't cached
- "Add to home screen" prompt: intercept the browser's `beforeinstallprompt` event; surface it as a dismissible banner ("Install PimPam as an app")

---

### Accessibility requirements (non-negotiable per project principles)

These must be verified on every component before it is considered done:

- All interactive elements keyboard-navigable (correct Tab order; Enter/Space activates buttons)
- All images have meaningful `alt` text; avatar `alt` = `@username`
- Color contrast meets WCAG 2.1 AA: 4.5:1 for body text, 3:1 for large text and UI components
- `:focus-visible` outlines never removed — only `:focus` (mouse) may be hidden
- Icon-only buttons (vote arrows, close modal, menu) must have `aria-label`
- Error messages use `role="alert"` (already in Login/Register — maintain this pattern)
- Semantic HTML throughout: `<nav>`, `<main>`, `<article>`, `<section>`, `<header>`, `<footer>`, `<aside>` — no `<div>` soup
- Respect `prefers-reduced-motion`: disable or reduce transitions and animations

---

### Implementation priority order

| Phase | What | Why first |
|---|---|---|
| 0 | **Backend prerequisites** — stories model + endpoints, unified feed query | Must exist before frontend can use them |
| 1 | Infrastructure (AuthContext, 5-tab shell, API modules, shared components) | Everything else renders inside the shell |
| 2 | Auth flows (email verification, TOTP step, password reset, consent checkboxes) | Blocks users from using the app otherwise |
| 3 | Feed + stories row + compose form | Core content loop |
| 4 | PostCard rewrite | Core content loop |
| 5 | Post detail + comments | Core content loop |
| 6 | User profiles + follow/unfollow | Social graph |
| 7 | Communities (dual-view tab + community pages) | Content organisation |
| 8 | Notifications | Re-engagement |
| 9 | Search | Discovery |
| 10 | Direct messages 1-on-1 (without E2EE first, add encryption as a follow-up) | Communication |
| 11 | Settings (account + GDPR data page) | Compliance |
| 12 | Moderation panel | Required before public launch |
| 13 | WS event handling (wired throughout phases above) | Real-time polish |
| 14 | PWA + service worker | Offline + installable |
| 15 | DM E2EE key management | Security hardening |
