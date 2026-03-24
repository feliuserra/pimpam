Posts
=====

Base path: ``/api/v1/posts``

Write endpoints require authentication. Read endpoints are public.

.. note::

   Rate limits: ``POST /posts`` — 10/min · ``PATCH /posts/{id}`` — 20/min ·
   ``POST|DELETE /posts/{id}/vote`` — 30/min.

----

Create a post
-------------

.. code-block:: http

   POST /api/v1/posts

Create a new post. A post must have either ``content`` or a ``url`` (or both).
Optionally scoped to a community via ``community_id``.

The author receives an automatic **+1 karma vote** at creation — this vote cannot
be changed or retracted. Post ``karma`` starts at ``1``.

**Request body**

.. code-block:: json

   {
     "title": "Interesting article",
     "content": "Here are my thoughts...",
     "url": "https://example.com/article",
     "community_id": null
   }

**Validation rules**

- At least one of ``content`` or ``url`` must be provided
- ``title``: max 300 characters

**Response** ``201 Created``

.. code-block:: json

   {
     "id": 1,
     "title": "Interesting article",
     "content": "Here are my thoughts...",
     "url": "https://example.com/article",
     "author_id": 1,
     "community_id": null,
     "karma": 1,
     "is_edited": false,
     "edited_at": null,
     "is_removed": false,
     "created_at": "2026-03-22T17:00:00Z"
   }

----

Get a post
----------

.. code-block:: http

   GET /api/v1/posts/{post_id}

Fetch a single post by ID. Removed posts return ``404``.

**Errors**

- ``404`` — post not found or removed

----

Edit a post
-----------

.. code-block:: http

   PATCH /api/v1/posts/{post_id}

Edit a post within **1 hour of creation**. Only the author may edit.
All fields are optional — only send what you want to change.

The response will include ``"is_edited": true`` and a non-null ``edited_at``.
Edit history is intentionally not stored — only the flag is public.

**Request body**

.. code-block:: json

   {
     "title": "Updated title",
     "content": "Updated content"
   }

**Response** ``200 OK`` — updated post object.

**Errors**

- ``403`` — not the author, or edit window has closed (1 hour after posting)
- ``404`` — post not found

----

Delete a post
-------------

.. code-block:: http

   DELETE /api/v1/posts/{post_id}

Permanently delete a post. Only the original author can delete their own post.

**Response** ``204 No Content``

**Errors**

- ``403`` — post belongs to another user
- ``404`` — post not found

----

Vote on a post
--------------

.. code-block:: http

   POST /api/v1/posts/{post_id}/vote

Cast or change a vote. Direction must be ``1`` (upvote) or ``-1`` (downvote).
Voting on your own post is not allowed — authors receive an automatic ``+1`` at creation.

Casting a vote when one already exists **changes** it (no duplicate vote error).
Both ``Post.karma`` and the author's ``User.karma`` are updated atomically.

**Request body**

.. code-block:: json

   { "direction": 1 }

**Response** ``200 OK``

.. code-block:: json

   { "post_id": 1, "direction": 1 }

**Errors**

- ``403`` — cannot vote on your own post
- ``404`` — post not found or removed
- ``422`` — direction not in ``{1, -1}``

----

Retract a vote
--------------

.. code-block:: http

   DELETE /api/v1/posts/{post_id}/vote

Remove your vote from a post. You cannot retract the author's automatic initial vote.
Karma on the post and the author is adjusted accordingly.

**Response** ``204 No Content``

**Errors**

- ``403`` — cannot retract your author vote
- ``404`` — post not found, or no vote to retract
