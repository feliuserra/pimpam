Moderation
==========

Base path: ``/api/v1/communities/{name}/...``

All moderation endpoints require authentication and moderator status
in the target community. Community creators are moderators automatically.

----

Remove a post
-------------

.. code-block:: http

   DELETE /api/v1/communities/{name}/posts/{post_id}

Hide a post from public view. The post is **not deleted** — it remains in the
database and is visible to moderators (``is_removed: true``).

**Response** ``204 No Content``

**Errors**

- ``403`` — not a moderator of this community
- ``404`` — post not found in this community

----

Restore a post
--------------

.. code-block:: http

   POST /api/v1/communities/{name}/posts/{post_id}/restore

Undo a post removal. The post becomes publicly visible again.

**Response** ``204 No Content``

**Errors**

- ``403`` — not a moderator of this community
- ``404`` — post not found in this community

----

Propose a ban
-------------

.. code-block:: http

   POST /api/v1/communities/{name}/bans

Propose banning a user from this community. Requires a Code of Conduct
violation reason. The proposer's vote is counted automatically.

A ban takes effect once **10 moderator votes** are reached.

**Request body**

.. code-block:: json

   {
     "target_username": "bob",
     "reason": "Repeated spam in multiple threads",
     "coc_violation": "spam",
     "is_permanent": false,
     "expires_at": "2026-06-01T00:00:00Z"
   }

.. list-table:: ``coc_violation`` values
   :header-rows: 1
   :widths: 30 70

   * - Value
     - Description
   * - ``harassment``
     - Targeted harassment of a user.
   * - ``hate_speech``
     - Hate speech or discriminatory content.
   * - ``abuse``
     - Abusive behaviour.
   * - ``spam``
     - Spam or unsolicited promotion.
   * - ``impersonation``
     - Impersonating another person or entity.
   * - ``nsfw_without_warning``
     - NSFW content posted without a content warning.
   * - ``other``
     - Other CoC violation (describe in ``reason``).

**Response** ``201 Created``

.. code-block:: json

   {
     "id": 1,
     "community_id": 1,
     "target_user_id": 2,
     "proposed_by_id": 1,
     "reason": "Repeated spam in multiple threads",
     "coc_violation": "spam",
     "is_permanent": false,
     "expires_at": "2026-06-01T00:00:00Z",
     "vote_count": 1,
     "required_votes": 10,
     "status": "pending",
     "created_at": "2026-03-22T17:00:00Z"
   }

**Errors**

- ``400`` — cannot propose banning yourself
- ``403`` — not a moderator
- ``404`` — target user not found

----

Vote on a ban proposal
----------------------

.. code-block:: http

   POST /api/v1/communities/{name}/bans/{proposal_id}/vote

Cast a vote in favour of a ban proposal. Each moderator can vote once.
When 10 votes are reached the ban is **applied automatically** and ``status``
becomes ``"approved"``.

**Response** ``200 OK`` — updated proposal object.

**Errors**

- ``403`` — not a moderator
- ``404`` — proposal not found or already resolved
- ``409`` — already voted on this proposal

----

List active bans
----------------

.. code-block:: http

   GET /api/v1/communities/{name}/bans

List all active bans in this community (moderators only). Expired bans are excluded.

**Response** ``200 OK``

.. code-block:: json

   [
     {
       "id": 1,
       "community_id": 1,
       "user_id": 2,
       "reason": "Repeated spam",
       "coc_violation": "spam",
       "is_permanent": false,
       "expires_at": "2026-06-01T00:00:00Z",
       "created_at": "2026-03-22T17:00:00Z"
     }
   ]

----

Propose a moderator promotion
------------------------------

.. code-block:: http

   POST /api/v1/communities/{name}/moderators

Propose promoting a community member to moderator. The target must already
be a member of the community. The proposer's vote is counted automatically.

Required votes: ``max(2, ceil(current_mod_count / 2))`` — a majority of
existing moderators, with a minimum of 2. This threshold is **locked at
proposal creation** and does not change if new mods are added mid-vote.

**Request body**

.. code-block:: json

   { "target_username": "carol" }

**Response** ``201 Created``

.. code-block:: json

   {
     "id": 1,
     "community_id": 1,
     "target_user_id": 3,
     "proposed_by_id": 1,
     "vote_count": 1,
     "required_votes": 2,
     "status": "pending",
     "created_at": "2026-03-22T17:00:00Z"
   }

**Errors**

- ``400`` — cannot propose yourself, or target is not a community member
- ``403`` — not a moderator
- ``404`` — target user not found

----

Vote on a mod promotion proposal
---------------------------------

.. code-block:: http

   POST /api/v1/communities/{name}/moderators/{proposal_id}/vote

Vote in favour of a mod promotion. When the required majority is reached,
the member is **promoted automatically** and ``status`` becomes ``"approved"``.

**Response** ``200 OK`` — updated proposal object.

**Errors**

- ``403`` — not a moderator
- ``404`` — proposal not found or already resolved
- ``409`` — already voted on this proposal
