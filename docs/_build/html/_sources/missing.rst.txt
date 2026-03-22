Missing & Planned Features
==========================

This page tracks functionality that is **stubbed, partially implemented, or not yet started**.
Cross off items here as they are completed.

----

Critical gaps (blocking basic usage)
-------------------------------------

Follow / Unfollow
~~~~~~~~~~~~~~~~~

**Status:** ✅ Implemented.

- ``POST /api/v1/users/{username}/follow``
- ``DELETE /api/v1/users/{username}/follow``

**Remaining TODO (federation):** Following remote (federated) users is local-only for now.
When a target user has ``is_remote=True``, the follow is stored locally but no AP ``Follow``
activity is sent to the remote server. To implement:

- Fetch the remote actor's inbox URL from the ``RemoteActor`` cache.
- Deliver an AP ``Follow`` activity via ``delivery.py``.
- Store the follow as ``pending`` until an ``Accept`` activity is received back.
- Handle the ``Accept`` response in ``activity_handler.py``.

----

Posts
-----

List posts by community
~~~~~~~~~~~~~~~~~~~~~~~

**Status:** ✅ Implemented — ``GET /api/v1/communities/{name}/posts``

Cursor-paginated, chronological. Moderators see removed posts.

Karma voting
~~~~~~~~~~~~

**Status:** ✅ Implemented.

- ``POST /api/v1/posts/{id}/vote`` — cast or change a vote (``{"direction": 1}`` or ``{"direction": -1}``)
- ``DELETE /api/v1/posts/{id}/vote`` — retract a vote

Rules: authors receive an automatic +1 on post creation and cannot vote on their own posts.
Vote changes update both ``Post.karma`` and the author's ``User.karma``.

**Remaining:** karma privilege thresholds (what karma unlocks) are not yet designed.

Edit a post
~~~~~~~~~~~

**Status:** ✅ Implemented — ``PATCH /api/v1/posts/{id}``

1-hour edit window enforced server-side. Edits are flagged publicly (``is_edited=True``,
``edited_at`` timestamp) but edit history is not stored.

----

Communities
-----------

List all communities
~~~~~~~~~~~~~~~~~~~~

**Status:** ✅ Implemented — ``GET /api/v1/communities?sort=popular|alphabetical|newest``

Page-based pagination (``page``, ``limit``).

Moderation tools
~~~~~~~~~~~~~~~~

**Status:** ✅ Implemented (core set).

- ``DELETE /api/v1/communities/{name}/posts/{post_id}`` — hide a post (reversible)
- ``POST /api/v1/communities/{name}/posts/{post_id}/restore`` — restore a hidden post
- ``POST /api/v1/communities/{name}/bans`` — propose a ban (CoC violation required)
- ``POST /api/v1/communities/{name}/bans/{id}/vote`` — vote on a ban proposal (auto-applies at 10 votes)
- ``GET /api/v1/communities/{name}/bans`` — list active bans (mods only)
- ``POST /api/v1/communities/{name}/moderators`` — propose mod promotion
- ``POST /api/v1/communities/{name}/moderators/{id}/vote`` — vote on promotion (majority of mods required)

**Remaining:**

- Transfer community ownership (owner → another moderator)
- Different moderator roles/tiers (planned for a future iteration)
- Appealing a ban (banned user perspective)

----

Messages
--------

Client-side encryption
~~~~~~~~~~~~~~~~~~~~~~~

**Status:** The server contract is in place (stores ciphertext only), but no
client-side encryption library is integrated in the React frontend yet.
The ``POST /messages`` endpoint accepts raw ciphertext — the frontend must
encrypt before calling it.

Inbox view
~~~~~~~~~~

**Status:** Not implemented.

``GET /api/v1/messages`` (list all conversations, grouped by user) does not exist.
Only ``GET /api/v1/messages/{user_id}`` (a single thread) is available.

Read receipts / mark as read
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Status:** ``Message.is_read`` field exists but is never updated.

----

Federation
----------

Outgoing delivery on post creation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Status:** ``delivery.py`` is implemented but never called.

When a local user creates a post, a ``Create{Note}`` activity should be delivered
to all followers' inboxes. The call site in ``POST /api/v1/posts`` is missing.

Follow initiation from local user
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Status:** Incoming follows from remote servers work. Outgoing follows (a local
user following a Mastodon account) do not — no endpoint sends the AP ``Follow`` activity.

Announce (boost / reblog)
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Status:** Not implemented. No AP ``Announce`` activity is sent or handled.

Like
~~~~

**Status:** Not implemented. No AP ``Like`` activity is sent or handled.

----

Infrastructure
--------------

Search
~~~~~~

**Status:** Meilisearch is in ``docker-compose.yml`` but nothing indexes to it
and no search endpoint exists.

Real-time (WebSockets)
~~~~~~~~~~~~~~~~~~~~~~~

**Status:** Not implemented. Live feed updates, message notifications, and
typing indicators all require a WebSocket layer.

Media uploads
~~~~~~~~~~~~~

**Status:** Not implemented. ``User.avatar_url`` and ``Post.url`` accept external
URLs only. No upload endpoint, no object storage integration (MinIO/S3), no CDN.

2FA (TOTP)
~~~~~~~~~~

**Status:** Not implemented. Planned in ``SECURITY.md`` but no code exists.

Rate limiting on non-auth endpoints
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Status:** Only ``/auth/register`` and ``/auth/login`` are rate-limited.
Feed, post creation, and other write endpoints have no rate limits yet.
