Comments & Reactions
====================

Comments live under two base paths:

- ``/api/v1/posts/{post_id}/comments`` — create and list comments on a post
- ``/api/v1/comments/{comment_id}`` — act on a specific comment

Requires authentication for write operations. Read operations are public.

.. note::

   Rate limit: ``POST /posts/{id}/comments`` — 1 per 30 seconds per user.

----

Comment object
--------------

.. code-block:: json

   {
     "id": 1,
     "post_id": 42,
     "author_id": 5,
     "parent_id": null,
     "depth": 0,
     "content": "Great post!",
     "is_removed": false,
     "created_at": "2026-03-24T10:00:00Z",
     "reaction_counts": {"agree": 3, "love": 1},
     "reply_count": 2
   }

Deleted comments have ``content`` replaced with ``"[deleted]"`` and ``is_removed: true``.
The comment slot is preserved in the thread so the nesting context is not broken.

----

Create a comment
----------------

.. code-block:: text

   POST /api/v1/posts/{post_id}/comments

Create a top-level comment or a reply. Comments cannot be edited after posting.
Maximum nesting depth is 5 levels (depth 0–4).

**Request body**

.. code-block:: json

   {
     "content": "Really interesting!",
     "parent_id": null
   }

Set ``parent_id`` to the ID of an existing comment to create a reply.
A ``disagree`` reaction on the parent comment is activated automatically when you reply.

**Response** ``201 Created`` — the new comment object.

**Errors**

- ``400`` — max depth exceeded
- ``404`` — post or parent comment not found

----

List comments
-------------

.. code-block:: text

   GET /api/v1/posts/{post_id}/comments

List top-level comments (depth 0) on a post. Use ``GET /comments/{id}/replies`` to
fetch nested replies.

**Query parameters**

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Parameter
     - Description
   * - ``sort``
     - ``latest`` (default) or ``top`` (by total agree + love reactions).
   * - ``limit``
     - Maximum results to return (default: 50, max: 100).
   * - ``before_id``
     - Cursor for pagination — return comments with ``id < before_id``.

**Response** ``200 OK`` — array of comment objects.

----

List replies
------------

.. code-block:: text

   GET /api/v1/comments/{comment_id}/replies

List direct replies to a comment, ordered oldest first.

**Response** ``200 OK`` — array of comment objects.

**Errors**

- ``404`` — comment not found

----

Delete a comment
----------------

.. code-block:: text

   DELETE /api/v1/comments/{comment_id}

Soft-delete your own comment. The slot remains visible in the thread with content
replaced by ``[deleted]``. You cannot delete someone else's comment; moderators use
the moderation endpoints for that.

**Response** ``204 No Content``

**Errors**

- ``403`` — not your comment
- ``404`` — comment not found
- ``409`` — comment is already removed (mod-removed)

----

Add a reaction
--------------

.. code-block:: text

   POST /api/v1/comments/{comment_id}/reactions

React to a comment. Each user may cast multiple reaction types on the same comment,
but only once per type.

**Request body**

.. code-block:: json

   {"reaction_type": "agree"}

Valid types: ``agree``, ``love``, ``misleading``, ``disagree``.

**Karma effects on the comment author:**

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Reaction
     - Effect
   * - ``agree``
     - +1 karma
   * - ``love``
     - +2 karma
   * - ``misleading``
     - −2 karma
   * - ``disagree``
     - 0 karma (inactive until you also reply to the comment; rate-limited to 10/day)

**Response** ``204 No Content``

**Errors**

- ``403`` — cannot react to your own comment
- ``404`` — comment not found or removed
- ``409`` — already reacted with this type
- ``429`` — daily ``disagree`` limit reached (10/day)

----

Remove a reaction
-----------------

.. code-block:: text

   DELETE /api/v1/comments/{comment_id}/reactions/{reaction_type}

Remove a reaction you previously cast. The karma effect is reversed.

**Response** ``204 No Content``

**Errors**

- ``404`` — reaction not found
