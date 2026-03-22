Posts
=====

Base path: ``/api/v1/posts``

Write endpoints require authentication.

----

Create a post
-------------

.. code-block:: http

   POST /api/v1/posts

Create a new post. A post must have either ``content`` or a ``url`` (or both).
Optionally scoped to a community via ``community_id``.

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
     "karma": 0,
     "created_at": "2026-03-22T17:00:00Z"
   }

----

Get a post
----------

.. code-block:: http

   GET /api/v1/posts/{post_id}

Fetch a single post by ID.

**Errors**

- ``404`` — post not found

----

Delete a post
-------------

.. code-block:: http

   DELETE /api/v1/posts/{post_id}

Delete a post. Only the original author can delete their own post.

**Response** ``204 No Content``

**Errors**

- ``403`` — post belongs to another user
- ``404`` — post not found

----

.. note::

   **Not yet implemented:** listing posts by community, karma voting (upvote/downvote),
   editing a post. See :doc:`../missing`.
