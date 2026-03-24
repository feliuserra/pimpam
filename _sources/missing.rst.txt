Missing & Planned Features
==========================

This page tracks functionality that is **stubbed, partially implemented, or not yet started**.
Cross off items here as they are completed.

----

Auth
----

Register / Login / Refresh
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Status:** ✅ Implemented.

- ``POST /api/v1/auth/register``
- ``POST /api/v1/auth/login`` — returns ``401 totp_required`` when 2FA is enabled and no code is provided
- ``POST /api/v1/auth/refresh``

Rate-limited: register 5/minute, login 10/minute.

Email Verification
~~~~~~~~~~~~~~~~~~

**Status:** ✅ Implemented.

Every new account starts **unverified**. A signed token is emailed on registration; users click the link (or hit ``GET /api/v1/auth/verify?token=<token>``) to activate their account. Tokens expire after 60 minutes.

- ``GET  /api/v1/auth/verify?token=<token>`` — verify email; token is single-use
- ``POST /api/v1/auth/resend-verification`` — issue a new token (authenticated, unverified users only; returns ``400`` if already verified)

Access gating: all endpoints that require ``CurrentUser`` return ``403 email_not_verified`` for unverified accounts. The only exceptions are ``GET /users/me``, ``PATCH /users/me``, ``POST /auth/logout``, account deletion routes, and all auth endpoints.

Expiry: unverified accounts that have not verified within 30 days are automatically hard-deleted by the hourly background task.

Password Reset
~~~~~~~~~~~~~~

**Status:** ✅ Implemented.

- ``POST /api/v1/auth/password-reset/request`` — send a reset email; returns ``202`` regardless of whether the address exists (no user enumeration). Rate-limited to 3 requests/hour per account.
- ``POST /api/v1/auth/password-reset/confirm`` — apply the new password. Accepts either a signed link token (15-minute expiry) or a 6-digit code (10-minute expiry).

On success: the user's ``token_version`` is incremented, invalidating all outstanding refresh tokens.

Logout / Change Password
~~~~~~~~~~~~~~~~~~~~~~~~

**Status:** ✅ Implemented.

- ``POST /api/v1/auth/logout`` — invalidate the current refresh token (server-side ``token_version`` bump); returns ``204``.
- ``POST /api/v1/auth/change-password`` — authenticated; requires current password. On success, ``token_version`` is bumped (forces re-login on all devices). Returns ``200``.

2FA (TOTP)
~~~~~~~~~~

**Status:** ✅ Implemented.

- ``POST /api/v1/auth/totp/setup`` — generates secret; returns provisioning URI + raw base32 (for QR code or manual entry). Does not activate 2FA yet.
- ``POST /api/v1/auth/totp/verify`` — confirms setup; activates 2FA.
- ``POST /api/v1/auth/totp/disable`` — requires current password + valid TOTP code.

TOTP secrets are AES-encrypted at rest (Fernet, keyed from ``ENCRYPTION_KEY``). Clock drift ±30 s tolerated.

----

Users
-----

**Status:** ✅ Implemented.

- ``GET  /api/v1/users/me`` — own profile (includes ``is_verified`` and ``deletion_scheduled_at``)
- ``PATCH /api/v1/users/me`` — update display name, bio, avatar URL
- ``GET  /api/v1/users/{username}`` — public profile
- ``POST /api/v1/users/{username}/follow`` — follow a user (federated: sends AP Follow, marks pending)
- ``DELETE /api/v1/users/{username}/follow`` — unfollow (federated: sends AP Undo{Follow})

Account Deletion
~~~~~~~~~~~~~~~~

**Status:** ✅ Implemented — hard delete with a 7-day grace period.

- ``POST /api/v1/users/me/delete`` — schedule deletion; requires current password. Returns ``202``. No-op if already scheduled (``409``).
- ``POST /api/v1/users/me/delete/cancel`` — cancel a pending deletion during the grace period. Returns ``200``. Returns ``400`` if nothing is scheduled.

Deletion cascade (executed after the 7-day grace period by the hourly background task):

- Posts and comments: ``author_id`` set to ``NULL`` — content stays visible as "[deleted user]".
- Messages *sent* by the user: ``sender_id`` set to ``NULL`` — the recipient keeps the message anonymised.
- Messages *received* by the user: deleted (they're private to the user).
- Everything else (votes, reactions, follows, karma, notifications, moderation rows): hard-deleted in FK-safe order.
- The ``User`` row itself is then hard-deleted.

The account remains fully functional during the grace period; deletion can be cancelled at any time before the background task runs.

----

Feed
----

**Status:** ✅ Implemented — ``GET /api/v1/feed``

Chronological posts from followed users, newest first. Cursor-paginated (``before_id``).
Pending federated follows are excluded until the remote server sends Accept.

----

Posts
-----

**Status:** ✅ Implemented.

- ``POST  /api/v1/posts`` — create a post (optionally in a community)
- ``GET   /api/v1/posts/{id}`` — fetch a single post
- ``PATCH /api/v1/posts/{id}`` — edit within 1-hour window (author only)
- ``DELETE /api/v1/posts/{id}`` — delete (author only)
- ``POST  /api/v1/posts/{id}/vote`` — cast or change vote (``{"direction": 1}`` or ``-1``)
- ``DELETE /api/v1/posts/{id}/vote`` — retract vote
- ``POST  /api/v1/posts/{id}/boost`` — AP Announce to remote followers (federated posts only)
- ``POST  /api/v1/posts/{id}/share`` — reshare a post to followers (and optionally a community)

Voting rules: authors receive an automatic +1 on creation and cannot vote on their own posts.
Votes update ``Post.karma``, ``User.karma`` (global), and ``CommunityKarma`` (per-community, if the post belongs to a community).

Sharing rules: one share per user per post. Sharing a share links to the root original.
When a share receives a ``+1`` vote, the original post author earns a ``+1`` karma bonus.

**Multiple images per post:** ✅ Schema ready — ``PostImage`` table + ``MULTI_IMAGE_POSTS_ENABLED`` flag.
Set the flag to ``true`` to allow up to ``POST_MAX_IMAGES`` images per post (default 10).
Frontend gallery UI not yet built.

----

Comments
--------

**Status:** ✅ Implemented.

- ``POST   /api/v1/posts/{id}/comments`` — create a comment or reply (``parent_id`` for nesting)
- ``GET    /api/v1/posts/{id}/comments`` — list top-level comments (``?sort=latest|top``, cursor-paginated)
- ``GET    /api/v1/comments/{id}/replies`` — list direct replies to a comment (oldest first)
- ``DELETE /api/v1/comments/{id}`` — author soft-deletes own comment (shown as ``[deleted]``)

Nesting depth: up to 5 levels (depth 0–4). Comments cannot be edited — delete and repost.
Character limit: 300 characters (configured via ``COMMENT_MAX_LENGTH`` in settings).

Reactions
~~~~~~~~~

- ``POST   /api/v1/comments/{id}/reactions`` — add a reaction (``agree``, ``disagree``, ``love``, ``misleading``)
- ``DELETE /api/v1/comments/{id}/reactions/{type}`` — remove a reaction

Reaction rules:

- Multiple reaction types per comment per user are allowed.
- Reactions affect the commenter's global karma directly (no karma counter on the comment itself).
- ``agree`` → ``+1`` karma; ``love`` → ``+2`` karma; ``misleading`` → ``-2`` karma.
- ``disagree`` → **0 karma effect**; starts inactive and activates only when the reactor also leaves a reply on the same comment. Rate-limited to 10 disagrees per user per day.

Moderation (comments)
~~~~~~~~~~~~~~~~~~~~~

- ``DELETE /api/v1/communities/{name}/comments/{id}`` — mod removes a comment (soft delete, reversible)
- ``POST   /api/v1/communities/{name}/comments/{id}/restore`` — mod restores a removed comment

WebSocket event: ``new_comment`` — delivered to the post author and all users who have commented on the post (excluding the commenter).

----

Communities
-----------

**Status:** ✅ Implemented.

- ``GET  /api/v1/communities`` — list all (``?sort=popular|alphabetical|newest``, paginated)
- ``POST /api/v1/communities`` — create (creator becomes owner, rate-limited 5/minute)
- ``GET  /api/v1/communities/{name}`` — community detail
- ``GET  /api/v1/communities/{name}/posts`` — chronological posts, cursor-paginated
- ``POST /api/v1/communities/{name}/join``
- ``POST /api/v1/communities/{name}/leave``
- ``GET  /api/v1/communities/{name}/members/{username}/karma`` — member's community karma + role

----

Karma System
------------

**Status:** ✅ Implemented (two-tier: global + per-community).

Global karma
~~~~~~~~~~~~

``User.karma`` — the sum of all votes received across all posts. Shown on the user's profile.
Updated automatically on every vote cast or retracted.

Community karma
~~~~~~~~~~~~~~~

``CommunityKarma.karma`` — per-community karma earned from votes on posts within that community.
Exposed at ``GET /api/v1/communities/{name}/members/{username}/karma``.

Community karma thresholds and what they unlock:

+----------+------------------+--------------------------------------+
| Karma    | Role milestone   | Unlocks                              |
+==========+==================+======================================+
| 50       | trusted_member   | Vote on ban proposals and appeals    |
+----------+------------------+--------------------------------------+
| 200      | (eligibility)    | Can be nominated as moderator        |
+----------+------------------+--------------------------------------+
| 500      | (eligibility)    | Can be nominated as senior_mod       |
+----------+------------------+--------------------------------------+

Role transitions are automatic: reaching 50 community karma promotes a ``member`` to
``trusted_member``; dropping below 50 reverts to ``member``. Appointed roles
(``moderator``, ``senior_mod``, ``owner``) are never auto-downgraded by karma loss.

**Remaining:**

- Karma privilege thresholds beyond mod eligibility (e.g. rate-limit relaxation, community creation)
- Mod rewards / separate moderation karma track (intentionally kept separate from vote-based karma)

----

Moderation
----------

Role hierarchy
~~~~~~~~~~~~~~

``member`` → ``trusted_member`` → ``moderator`` → ``senior_mod`` → ``owner``

+---------------------+------------------+-----------+------------+-------+
| Action              | trusted_member   | moderator | senior_mod | owner |
+=====================+==================+===========+============+=======+
| Vote on ban props.  | ✅               | ✅        | ✅         | ✅    |
+---------------------+------------------+-----------+------------+-------+
| Remove/restore post | ❌               | ✅        | ✅         | ✅    |
+---------------------+------------------+-----------+------------+-------+
| Propose ban         | ❌               | ✅        | ✅         | ✅    |
+---------------------+------------------+-----------+------------+-------+
| Vote on ban appeals | ❌               | ✅        | ✅         | ✅    |
+---------------------+------------------+-----------+------------+-------+
| Promote mods        | ❌               | ❌        | ✅         | ✅    |
+---------------------+------------------+-----------+------------+-------+
| Ownership transfer  | ❌               | ❌        | ✅         | ✅    |
+---------------------+------------------+-----------+------------+-------+

Post removal
~~~~~~~~~~~~

**Status:** ✅ Implemented.

- ``DELETE /api/v1/communities/{name}/posts/{post_id}`` — hide a post (reversible, requires moderator+)
- ``POST  /api/v1/communities/{name}/posts/{post_id}/restore`` — restore a hidden post

Bans
~~~~

**Status:** ✅ Implemented.

- ``POST /api/v1/communities/{name}/bans`` — propose a ban (CoC violation required, moderator+)
- ``POST /api/v1/communities/{name}/bans/{id}/vote`` — vote on a proposal (trusted_member+, auto-applies at 10 votes)
- ``GET  /api/v1/communities/{name}/bans`` — list active bans (moderator+)

Ban appeals
~~~~~~~~~~~

**Status:** ✅ Implemented.

- ``POST /api/v1/communities/{name}/appeals`` — submit an appeal (banned user, 1-week cooldown, one pending appeal at a time)
- ``POST /api/v1/communities/{name}/appeals/{id}/vote`` — vote to overturn (moderator+, blocked if you voted on the original ban)
- ``GET  /api/v1/communities/{name}/appeals`` — list pending appeals (moderator+)

10 votes required to overturn. If overturned: ban row kept with ``status="overturned"``
(transparent record — moderation is never silently deleted).

Moderator promotion
~~~~~~~~~~~~~~~~~~~

**Status:** ✅ Implemented.

- ``POST /api/v1/communities/{name}/moderators`` — propose promotion to ``moderator`` or ``senior_mod`` (senior_mod+). Target must have 200+ community karma for moderator, 500+ for senior_mod.
- ``POST /api/v1/communities/{name}/moderators/{id}/vote`` — vote on promotion (senior_mod+, auto-applies at majority)

Ownership transfer
~~~~~~~~~~~~~~~~~~

**Status:** ✅ Implemented.

- ``POST /api/v1/communities/{name}/ownership-transfer`` — propose transfer to any member (senior_mod+, cancels any existing pending transfer)
- ``POST /api/v1/communities/{name}/ownership-transfer/{id}/respond`` — accept or reject (recipient only)

On acceptance: old owner is demoted to ``moderator``, recipient is promoted to ``owner``,
``Community.owner_id`` is updated.

**Remaining:**

- Moderator tiers with finer-grained permissions (current two-tier: moderator / senior_mod)
- Ban reason history visible to the banned user

----

Messages
--------

**Status:** ✅ Implemented (server contract only — client-side encryption not yet integrated in the React frontend).

- ``POST  /api/v1/messages`` — send a message (stores ciphertext only; client must encrypt)
- ``GET   /api/v1/messages`` — inbox: one entry per conversation partner with unread count
- ``GET   /api/v1/messages/{other_user_id}`` — conversation thread (newest first, last 50)
- ``PATCH /api/v1/messages/{other_user_id}/read`` — mark all messages from that user as read

The server stores only ciphertext and encrypted keys — it never holds plaintext message content.

----

Media
-----

**Status:** ✅ Implemented — ``POST /api/v1/media/upload``

- Accepts JPEG, PNG, WebP, GIF up to 10 MB.
- Converts to WebP and strips EXIF metadata (including GPS) server-side via Pillow.
- Avatars resized to 512×512 px. Post images resized to 2000 px on longest side.
- Uploads to S3-compatible storage (MinIO in dev, Cloudflare R2 in prod).
- Returns a public URL for use in ``PATCH /users/me`` or ``POST /posts``.

**Not yet implemented:**

- Content hash-matching against NCMEC database
- Multiple images per post UI — schema and flag are in place; set ``MULTI_IMAGE_POSTS_ENABLED=true`` to activate; the frontend gallery UI is not yet built
- User-provisioned storage (BYOS)

----

Search
------

**Status:** ✅ Implemented — ``GET /api/v1/search``

- Full-text search across three Meilisearch indexes: ``posts`` (title, content, URL), ``users`` (username, bio), and ``communities`` (name, description).
- Optional ``?type=post|user|community`` scopes results to one kind (defaults to all three, fan-out search).
- Optional ``?community=<name>`` further scopes post results to one community.
- Removed posts always excluded.
- All three indexes are updated automatically on create/edit/delete (fire-and-forget).
- Returns ``503`` if ``SEARCH_ENABLED=false`` or Meilisearch is unreachable.

----

Real-time (WebSockets)
----------------------

**Status:** ✅ Implemented — ``WS /ws?token=<access_token>``

One persistent connection per authenticated user, backed by Redis pub/sub.

Events pushed to the client:

- ``new_post`` — a followed user published or reshared a post
- ``new_comment`` — a comment was posted on a thread you are watching (post author + prior commenters)
- ``new_message`` — a DM was received
- ``karma_update`` — one of the user's posts was voted on

Connection closes after 60 s of client silence; clients reconnect (no replay).
Redis downtime never breaks primary operations.

**Typing indicators:** ✅ Implemented. Clients send ``{"type": "typing", "recipient_id": N}`` over
the WS connection; the server forwards a ``typing`` event to the recipient's channel immediately.

**Not yet implemented:**

- Live community activity (new posts in a community the user is browsing)

----

Federation (ActivityPub)
------------------------

**Status:** ✅ Implemented — gated by ``FEDERATION_ENABLED`` env flag.

Discovery
~~~~~~~~~

- ``GET /.well-known/webfinger?resource=acct:{user}@{domain}``
- ``GET /nodeinfo/2.1``

Actor
~~~~~

- ``GET /users/{username}`` — Person actor document (with RSA public key)

Inbox / Outbox
~~~~~~~~~~~~~~

- ``POST /users/{username}/inbox`` — receive activities (verified HTTP Signature)
- ``GET  /users/{username}/outbox`` — AP OrderedCollection of local posts
- ``GET  /users/{username}/followers``
- ``GET  /users/{username}/following``
- ``POST /inbox`` — shared inbox

Outgoing activities
~~~~~~~~~~~~~~~~~~~

- **Create{Note}** — delivered to remote followers on post creation
- **Follow / Undo{Follow}** — sent when following/unfollowing a remote user; stored as ``is_pending=True`` until Accept received
- **Accept** — sent in response to incoming Follow
- **Like / Undo{Like}** — sent on +1 vote / retract on federated posts
- **Announce** — ``POST /api/v1/posts/{id}/boost`` (federated posts only)

----

Infrastructure
--------------

Rate limiting
~~~~~~~~~~~~~

**Status:** ✅ Implemented via ``slowapi``.

+-----------------------------------------+-----------+
| Endpoint                                | Limit     |
+=========================================+===========+
| POST /auth/register                     | 5/minute  |
+-----------------------------------------+-----------+
| POST /auth/login                        | 10/minute |
+-----------------------------------------+-----------+
| POST /posts                             | 10/minute |
+-----------------------------------------+-----------+
| PATCH /posts/{id}                       | 20/minute |
+-----------------------------------------+-----------+
| POST|DELETE /posts/{id}/vote            | 30/minute |
+-----------------------------------------+-----------+
| POST /posts/{id}/boost                  | 30/minute |
+-----------------------------------------+-----------+
| GET /feed                               | 60/minute |
+-----------------------------------------+-----------+
| POST /communities                       | 5/minute  |
+-----------------------------------------+-----------+
| POST /users/{username}/follow           | 20/minute |
+-----------------------------------------+-----------+
| POST /messages                          | 20/minute |
+-----------------------------------------+-----------+

CI / CD
~~~~~~~

**Status:** ✅ Implemented — ``.github/workflows/ci.yml``

- Runs on every branch push and on PRs targeting ``main``.
- pytest with coverage; fails if overall coverage drops below 70 %.
- Coverage report written to the GitHub Actions job summary.
- Branch protection on ``main``: merge blocked until ``Tests & Coverage`` passes.

----

Notifications
-------------

**Status:** ✅ Implemented.

- ``GET    /api/v1/notifications`` — inbox, unread first then read, newest first (``?limit=20&before_id=``)
- ``GET    /api/v1/notifications/unread-count`` — badge counter
- ``PATCH  /api/v1/notifications/{id}/read`` — mark one notification as read
- ``PATCH  /api/v1/notifications/read-all`` — mark all notifications as read
- ``GET    /api/v1/notifications/preferences`` — list disabled notification types
- ``PATCH  /api/v1/notifications/preferences`` — enable or disable a type (body: ``{"notification_type": "vote", "enabled": false}``)

Notification types:

+----------------------+---------+-------------------------------------------+
| Type                 | Grouped | Trigger                                   |
+======================+=========+===========================================+
| ``reply``            | no      | Someone replied to your comment           |
+----------------------+---------+-------------------------------------------+
| ``reaction``         | yes     | Someone reacted to your comment           |
+----------------------+---------+-------------------------------------------+
| ``new_comment``      | yes     | Someone commented on your post            |
+----------------------+---------+-------------------------------------------+
| ``share``            | no      | Someone shared your post                  |
+----------------------+---------+-------------------------------------------+
| ``follow``           | no      | Someone followed you                      |
+----------------------+---------+-------------------------------------------+
| ``vote``             | yes     | Someone voted on your post                |
+----------------------+---------+-------------------------------------------+
| ``post_removed``     | no      | A mod removed your post                   |
+----------------------+---------+-------------------------------------------+
| ``comment_removed``  | no      | A mod removed your comment                |
+----------------------+---------+-------------------------------------------+
| ``ban_proposed``     | no      | A ban was proposed against you            |
+----------------------+---------+-------------------------------------------+
| ``banned``           | no      | You were banned from a community          |
+----------------------+---------+-------------------------------------------+
| ``appeal_resolved``  | no      | Your ban appeal was resolved              |
+----------------------+---------+-------------------------------------------+
| ``mod_nominated``    | no      | You were nominated for mod promotion      |
+----------------------+---------+-------------------------------------------+
| ``mod_promoted``     | no      | You were promoted to a mod role           |
+----------------------+---------+-------------------------------------------+
| ``ownership_offered``| no      | You were offered community ownership      |
+----------------------+---------+-------------------------------------------+

**Grouping:** Grouped types (reactions, votes, new comments) upsert into a single unread row per
group key, incrementing ``group_count``. Marking a grouped notification as read closes the group;
subsequent events start fresh. The DB stores the real count — clients should render ``>99`` when
``group_count > 99``.

**Preferences:** All types are enabled by default. A ``NotificationPreference`` row is only
created when a type is disabled (opt-out list). No rows = all on.

**Delivery:** Every notification is stored immediately and a ``notification`` WebSocket event is
pushed to the user if connected. Failure of either step never breaks the triggering operation.

----

Not yet started
---------------

- **React frontend** — the ``client/`` directory exists but the UI is a skeleton.
- **Multiple images per post UI** — schema and ``MULTI_IMAGE_POSTS_ENABLED`` flag are in place; only the frontend gallery UI is missing.
- **NCMEC content hash-matching** — post-upload async check.
- **BYOS (user-provisioned storage)** — optional power-user bucket.
- **Karma beyond mod eligibility** — rate-limit relaxation, community creation gating.
- **Mod rewards / separate moderation karma** — planned but intentionally separate from vote-based karma.
