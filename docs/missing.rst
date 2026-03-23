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

**Status:** ✅ Implemented — ``GET /api/v1/messages``

Returns one ``ConversationSummary`` per conversation partner: other user ID,
username, last message timestamp, and unread count. Ordered newest first.

Read receipts / mark as read
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Status:** ✅ Implemented — ``PATCH /api/v1/messages/{other_user_id}/read``

Marks all messages from ``other_user_id`` to the current user as read.
Call when the user opens a conversation thread.

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

**Status:** ✅ Implemented — ``POST /api/v1/media/upload``

- Accepts JPEG, PNG, WebP, GIF up to 10 MB.
- Converts to WebP and strips EXIF metadata (including GPS) server-side via Pillow.
- Avatars resized to 512×512 px. Post images resized to 2000 px on longest side.
- Uploads to S3-compatible storage (MinIO in dev, Cloudflare R2 in prod).
- Returns a public URL. Client uses it in ``PATCH /users/me`` or ``POST /posts``.

**Not yet implemented:**

- Content hash-matching against NCMEC database (catches known illegal images).
  Add as an async post-upload check using the PhotoDNA or NCMEC API.
  Keep images in a ``pending`` state until the check passes.
- Multiple images per post — see below.

See *User-provisioned storage (BYOS)* below for a scalable alternative to
a centrally hosted bucket.

Multiple images per post
~~~~~~~~~~~~~~~~~~~~~~~~

**Status:** Not implemented. Current schema supports one ``image_url`` per post.

To implement:

1. Create a ``PostImage`` model: ``id``, ``post_id`` (FK), ``url``, ``order`` (int).
2. Add ``Post.images`` as a ``relationship`` to ``PostImage``.
3. Remove ``Post.image_url`` column (migration required).
4. Change ``PostCreate.image_url: str | None`` → ``PostCreate.image_urls: list[str]``.
5. Update ``PostPublic`` to include ``images: list[str]``.
6. The upload endpoint (``POST /api/v1/media/upload``) stays unchanged —
   clients call it once per image and collect the URLs before creating the post.

User-provisioned storage (BYOS)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Status:** Not implemented. Planned as an *optional* power-user feature on top
of the default centrally-hosted storage.

**Default behaviour:** PimPam hosts media centrally (MinIO/S3). Zero setup
required — works out of the box for all users.

**Optional BYOS:** power users or self-hosters can plug in their own bucket
(Backblaze B2, Cloudflare R2, AWS S3, etc.) for full data sovereignty.

To implement:

- Add encrypted fields to ``User``: ``storage_provider``, ``storage_bucket``,
  ``storage_access_key`` (AES-encrypted at rest), ``storage_secret_key`` (AES-encrypted).
- ``PATCH /api/v1/users/me/storage`` — configure a personal bucket (optional).
- ``POST /api/v1/media/upload-url`` — server generates a pre-signed URL pointing
  to either PimPam's central bucket or the user's own bucket; client uploads directly.
- Store the resulting public URL in ``User.avatar_url`` or ``Post.url``.

Benefits for BYOS users: data stays in their own bucket, GDPR erasure is trivial,
no dependency on PimPam's storage infrastructure.

Rate limiting on non-auth endpoints
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Status:** ✅ Implemented. All write endpoints and the feed are now rate-limited:

- ``POST /posts`` — 10/minute
- ``PATCH /posts/{id}`` — 20/minute
- ``POST /posts/{id}/vote``, ``DELETE /posts/{id}/vote`` — 30/minute
- ``GET /feed`` — 60/minute
- ``POST /communities`` — 5/minute
- ``POST /users/{username}/follow`` — 20/minute
- ``POST /messages`` — 20/minute

2FA (TOTP)
~~~~~~~~~~

**Status:** Not implemented. Planned — no code exists yet.

To implement:

- Add ``totp_secret`` (AES-encrypted) and ``totp_enabled`` fields to ``User`` model.
- ``POST /auth/totp/setup`` — generate a TOTP secret, return QR code URI.
- ``POST /auth/totp/verify`` — confirm setup by validating a code.
- ``POST /auth/totp/disable`` — require password + current TOTP code to disable.
- Require TOTP code as a second login step when ``totp_enabled=True``.
- Use the ``pyotp`` library.
