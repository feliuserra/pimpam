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

All core backend features are implemented and covered by integration tests (`pytest -v`).

**Implemented:**
- Auth: register, login, refresh (bcrypt + JWT, rate-limited)
- 2FA (TOTP): setup, verify, disable; second login step; secrets AES-encrypted at rest
- Password reset: link mode (15 min, URL token) or code mode (6-digit, 10 min); client chooses via `mode` field; SMTP delivery (no-op in dev); rate-limited 3/hour per account; resets increment `User.token_version` to revoke all refresh tokens; 404 for unknown email (deliberate)
- Logout: `POST /auth/logout` — bumps `token_version`, invalidating all refresh tokens; returns 204
- Change password: `POST /auth/change-password` — requires current password; bumps `token_version` (forces re-login everywhere); returns 200
- Email verification: token emailed on register (60-min expiry, single-use, SHA-256 hash stored); `GET /auth/verify?token=` to activate; `POST /auth/resend-verification` for new token; `CurrentUser` dep returns 403 `email_not_verified` if unverified; unverified accounts auto-deleted after 30 days by hourly background task
- Account deletion: `POST /users/me/delete` schedules hard-delete with 7-day grace period (password required); `POST /users/me/delete/cancel` cancels; hourly task executes due deletions — posts/comments anonymised (author_id=NULL), sent messages anonymised (sender_id=NULL), received messages deleted, everything else purged, then user row hard-deleted
- Chronological feed, cursor-paginated
- Posts: create, edit (1-hour window), delete, vote (+1/-1), karma propagation, boost (AP Announce), share (reshare to followers/community)
- Comments: create (up to 5 levels nesting), list (sort: latest/top), replies, author soft-delete, reactions (agree/love/misleading/disagree), mod remove/restore
- Comment reactions: agree (+1 karma), love (+2), misleading (−2), disagree (0, activates on reply, 10/day limit)
- Communities: create, list (sort: popular/alphabetical/newest), join/leave, post listing
- Two-tier karma: global (`User.karma`) + per-community (`CommunityKarma`) with automatic role promotion at 50 community karma
- Moderation role hierarchy: member → trusted_member → moderator → senior_mod → owner
- Moderation: remove/restore posts, ban proposals (10-vote consensus), ban appeals (10-vote overturn, 1-week cooldown, original voters excluded), mod promotion (karma-gated, majority vote), ownership transfer (accept/reject flow)
- Follow/unfollow (local and federated users, with pending state)
- Direct messages: send (E2EE ciphertext only), inbox, conversation thread, mark as read
- Rate limiting on all write endpoints and feed
- Media uploads: JPEG/PNG/WebP/GIF → WebP, EXIF strip, resize, S3-compatible storage
- Search: full-text via Meilisearch over posts, users, and communities; `?type=post|user|community` filter; indexes wired into register, profile update, community create
- ActivityPub federation: WebFinger, NodeInfo, Actor, Inbox, Outbox, HTTP Signatures
- Federation outgoing delivery: Create{Note} on post, Follow/Undo{Follow}, Like/Undo{Like}, Announce — all gated by `FEDERATION_ENABLED`
- WebSocket real-time updates: `WS /ws?token=<jwt>` — new_post, new_comment, new_message, karma_update, notification events via Redis pub/sub; typing indicators (client sends `{"type":"typing","recipient_id":N}`, forwarded to recipient's channel)
- Notifications: persistent inbox, 14 event types, grouped reactions/votes/new_comments, per-type opt-out preferences, real-time WS push + stored
- Multi-image posts: `PostImage` table (post_id, url, display_order); `MULTI_IMAGE_POSTS_ENABLED` flag (default false, max 1); `POST_MAX_IMAGES=10` cap when enabled; `PostPublic` always returns `images: list`; `Post.image_url` kept as first-image cache for search/sharing compat

**Not yet implemented — see `docs/missing.rst` for full detail:**
- React frontend (client/ directory is a skeleton)
- Multiple images per post UI (schema + flag already in place; `MULTI_IMAGE_POSTS_ENABLED=true` to activate)
- NCMEC content hash-matching (post-upload async check)
- BYOS (user-provisioned storage)
- Karma privilege thresholds beyond mod eligibility (rate-limit relaxation, community creation gating)
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
