Missing & Planned Features
==========================

This page tracks functionality that is **stubbed, partially implemented, or not yet started**.
Cross off items here as they are completed.

----

Critical gaps (blocking basic usage)
-------------------------------------

These are missing from the current scaffold and prevent the app from being usable end-to-end.

Follow / Unfollow
~~~~~~~~~~~~~~~~~

**Status:** No endpoint exists yet.

The ``follows`` table and ``Follow`` model are in place, and the feed query
already reads from it — but there is no API endpoint to create or delete a Follow.
Until this exists, the feed will always return an empty list for every user.

**To implement:**

- ``POST /api/v1/users/{username}/follow`` — follow a user
- ``DELETE /api/v1/users/{username}/follow`` — unfollow a user
- For remote users: send an AP ``Follow`` activity to their inbox via ``delivery.py``

----

Posts
-----

List posts by community
~~~~~~~~~~~~~~~~~~~~~~~

**Status:** Not implemented.

``GET /api/v1/communities/{name}/posts`` does not exist.
Posts can be created with a ``community_id`` but there is no way to retrieve them by community.

Karma voting
~~~~~~~~~~~~

**Status:** Model field exists (``Post.karma``, ``User.karma``), no vote endpoint.

Need ``POST /api/v1/posts/{id}/vote`` with ``{"direction": 1}`` or ``{"direction": -1}``.
The karma engine logic (privilege thresholds, anti-abuse rules) is also undesigned.

Edit a post
~~~~~~~~~~~

**Status:** Not implemented.

``PATCH /api/v1/posts/{id}`` does not exist.

----

Communities
-----------

List all communities
~~~~~~~~~~~~~~~~~~~~

**Status:** Not implemented.

``GET /api/v1/communities`` (with pagination) does not exist.

Moderation tools
~~~~~~~~~~~~~~~~

**Status:** Not implemented.

- Remove a post from a community
- Ban a user from a community
- Promote a member to moderator
- Transfer community ownership

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
