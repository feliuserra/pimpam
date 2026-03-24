# PimPam

**A social platform made by the people, for the people.**

PimPam is an open-source, ad-free social network that puts humans first. No toxic algorithms deciding what you see. No corporations mining your data. No ads fighting for your attention. Just you, your friends, and the communities you care about.

---

## Why PimPam exists

The internet was supposed to connect us. Instead, we got platforms that treat people as products — feeding us algorithmic slop to maximize engagement, selling our attention to advertisers, and designing addictive interfaces that exploit our psychology.

PimPam is a rejection of all that.

> **The hypothesis:** Social networks are harmful because of how they're built and who they're built for — not because social connection itself is harmful. PimPam is an experiment in what happens when you remove the incentives that cause the harm: algorithmic amplification, surveillance capitalism, centralised control. We're removing those specific structural incentives and seeing what grows in their place.

We believe social media can be simple, honest, and human. A place where your feed shows posts from people you actually follow, in the order they were posted. Where communities form around shared interests, not outrage. Where your data belongs to you, full stop.

Think of the warmth of early MySpace, the simplicity of Tuenti, the community spirit of old-school Reddit, and the visual appeal of Instagram — without any of the corporate machinery that ruined them.

## What PimPam is

PimPam combines three core experiences into one platform:

**A chronological, human feed.** Your feed shows posts from the people you follow, ordered by time and grouped by user. No algorithmic ranking. No promoted content. No "suggested for you." If you follow someone, you see their posts. That's it.

**Communities for real discussion.** Topic-based spaces where people come together to talk, share, and learn — inspired by the best of Reddit's community model. Moderated by the community, for the community.

**Direct messaging.** Private conversations with your friends. End-to-end encrypted. No data harvesting. Just messages.

**A karma system rooted in ethics.** Contributions to the platform — helpful posts, thoughtful comments, community moderation — earn karma. This isn't about internet points; it's about recognizing people who make the community better.

## Our principles

These aren't marketing slogans. They're commitments baked into the code, the license, and the governance of this project.

1. **No toxic algorithms, ever.** Your feed is chronological. We don't want algorithmic sorting, recommendation engines, or engagement-optimization systems. If it's not from someone you chose to follow or a community you joined, it doesn't appear.

2. **No ads, ever.** PimPam will never show advertisements. Not "tasteful" ones. Not "relevant" ones. None. The platform is funded by its community, not by corporations.

3. **No data exploitation.** We collect the minimum data necessary to make the platform work. We don't sell it, share it, or analyze it for profit. You can export or delete your data at any time. Full GDPR compliance isn't a checkbox for us — it's a core value.

4. **Open source, forever.** Every line of code is public. The AGPL-3.0 license ensures that PimPam — and any fork of it — must remain open source. No company can take this code and build a closed, proprietary product from it.

5. **Owned by nobody.** PimPam has no CEO, no board of directors, no shareholders to please. Governance is community-driven. Decisions are made transparently, and everyone has a voice.

6. **Safe for everyone.** We take a zero-tolerance approach to harassment, hate speech, and abuse. The platform is designed to be safe and welcoming for all people, regardless of who they are or where they come from. See our [Code of Conduct](CODE_OF_CONDUCT.md).

7. **Privacy by design.** Privacy isn't a feature we bolt on — it's how we build everything. End-to-end encryption for messages. Minimal data collection. No tracking across the web. No fingerprinting. Your digital life is yours.

## Technical vision

PimPam is built with a modern, accessible stack designed for community contribution:

| Layer | Technology |
|-------|-----------|
| Frontend | React + Vite (PWA) |
| Backend | Python + FastAPI |
| Database | PostgreSQL |
| ORM | SQLAlchemy 2.0 (async) |
| Migrations | Alembic |
| Real-time | WebSockets via FastAPI + Redis pub/sub |
| Federation | ActivityPub (HTTP Signatures, WebFinger) |
| Search | Meilisearch (full-text over posts, users, and communities) |
| Media storage | S3-compatible (MinIO in dev, Cloudflare R2 in prod) |
| DM encryption | End-to-end (client-side keys; server stores ciphertext only) |
| Rate limiting | slowapi |
| Infrastructure | Docker Compose; designed to be self-hostable |

The architecture prioritizes simplicity, security, and the ability for anyone to contribute, audit, or fork the project.

## API overview

All features are exposed via a versioned REST API at `/api/v1/`. Interactive docs are available at `/docs` (Swagger UI) when running locally.

| Area | Endpoints |
|------|-----------|
| Auth | Register, login, refresh tokens, 2FA (TOTP), password reset (link or code, SMTP email) |
| Users | Own profile, public profile, follow/unfollow |
| Feed | Chronological feed from followed users (cursor-paginated) |
| Posts | Create, edit, delete, vote (+1/-1), boost (AP Announce), share (reshare to followers/community) |
| Comments | Nested threads (5 levels), sort by latest or top, author delete, mod remove/restore |
| Reactions | Per-comment reactions: agree (+1 karma), love (+2), misleading (−2), disagree (requires a reply, 10/day limit) |
| Communities | Create, list, join/leave, post listing, member karma |
| Moderation | Remove/restore posts and comments, ban proposals, ban appeals, mod promotion, ownership transfer |
| Messages | Send (E2EE), inbox, conversation thread, mark as read |
| Media | Upload images (JPEG/PNG/WebP/GIF → WebP, EXIF stripped, S3 storage) |
| Auth | Register, login, refresh tokens, 2FA (TOTP setup/verify/disable), password reset (link or code, email delivery) |
| Search | Full-text search over posts, users, and communities; `?type=post\|user\|community` filter |
| Notifications | Persistent inbox, 14 event types, grouped reactions/votes, per-type opt-out |
| Real-time | WebSocket at `WS /ws?token=<jwt>` — new_post, new_comment, new_message, karma_update, notification |
| Federation | ActivityPub: WebFinger, NodeInfo, Actor, Inbox, Outbox, HTTP Signatures |

## Project status

The core backend is complete and covered by an integration test suite (`pytest -v`). All API endpoints are implemented, documented, and rate-limited.

**What's working today:**
- Full auth flow with optional 2FA (TOTP, secrets encrypted at rest)
- Password reset — link mode (15 min) or code mode (6-digit, 10 min), delivered via SMTP, rate-limited to 3/hour per account; resets invalidate all outstanding refresh tokens
- Email verification — new accounts are gated until verified; tokens expire in 60 min; unverified accounts auto-deleted after 30 days; resend endpoint included
- Logout (server-side token invalidation) and change-password (requires current password, forces re-login on all devices)
- Account deletion — 7-day grace period with password confirmation; posts/comments anonymised, sent messages anonymised, received messages deleted; cancellable during grace period
- Chronological feed — strictly time-ordered, never algorithmic
- Posts: create, edit (1-hour window), vote, share (reshares trace to root original)
- Comments: nested threads up to 5 levels, sort by latest or most-reacted, author delete, mod remove/restore
- Comment reactions: agree, love, misleading, disagree — each with a distinct karma effect; disagree requires an accompanying reply to activate, capped at 10/day
- Two-tier karma: global (shown on profile) + per-community (unlocks trusted_member at 50, gates mod eligibility at 200/500)
- Communities with a full moderation system: role hierarchy (member → trusted_member → moderator → senior_mod → owner), ban proposals, ban appeals, mod promotion, ownership transfer
- End-to-end encrypted direct messages
- Real-time updates via WebSocket (new post, new comment, new message, karma update, notifications)
- Persistent notification inbox: 14 event types covering social actions and moderation, with grouped counts for reactions/votes, per-type opt-out preferences
- Full-text search via Meilisearch over posts, users, and communities; `?type=` filter to scope results
- ActivityPub federation — follow remote users, receive posts, boost content across the fediverse
- CI/CD with coverage enforcement (≥70%) on every push

**What's next:**
- Admin layer — platform-level moderation: site admin role, global bans, user suspension, platform content removal (required before public launch)
- React frontend (the `client/` directory is currently a skeleton)
- Multiple images per post
- Typing indicators in DMs
- Karma privilege thresholds (rate-limit relaxation, community creation gating for trusted users)

Want to help? Read our [Contributing Guide](CONTRIBUTING.md) and check the open issues.

## Getting involved

PimPam is nothing without its community. Here's how you can help:

- **Read the docs.** Start with this README, the [Contributing Guide](CONTRIBUTING.md), and the [Code of Conduct](CODE_OF_CONDUCT.md).
- **Join the discussion.** Open an issue to share ideas, ask questions, or propose features.
- **Contribute code.** Check out open issues, submit pull requests, and help build the platform.
- **Spread the word.** Tell people about PimPam. The more people who know, the stronger the community.
- **Report issues.** Found a bug or a security concern? See our [Security Policy](SECURITY.md).

## License

PimPam is licensed under the [GNU Affero General Public License v3.0](LICENSE). This means:

- You can use, modify, and distribute PimPam freely.
- Any modified version must also be open source under the same license.
- If you run a modified version as a network service, you must make the source code available to its users.

This license was chosen deliberately. It ensures that PimPam's code can never be captured by a corporation and turned into a closed product. The people's platform stays the people's platform.

---

**PimPam. No toxic algorithms. No ads. No BS. Just people.**
