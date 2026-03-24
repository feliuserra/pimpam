Feed
====

Base path: ``/api/v1/feed``

Requires authentication.

.. note::

   Rate limit: ``GET /feed`` — 60/min.

----

Get chronological feed
-----------------------

.. code-block:: http

   GET /api/v1/feed

Returns posts from users you follow, ordered newest first.
**There is no algorithmic ranking.** Order is always chronological — no ML, no engagement signals.

Removed posts are excluded from the feed.

Pagination is cursor-based via ``before_id`` — never offset-based,
which avoids duplicate or missing posts when new content arrives.

**Query parameters**

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Parameter
     - Default
     - Description
   * - ``limit``
     - ``20``
     - Number of posts to return. Maximum ``50``.
   * - ``before_id``
     - —
     - Return posts older than this post ID. Omit for the first page.

**Response** ``200 OK``

.. code-block:: json

   [
     {
       "id": 99,
       "title": "Hello from Bob",
       "content": "First post!",
       "url": null,
       "author_id": 2,
       "community_id": null,
       "karma": 1,
       "is_edited": false,
       "edited_at": null,
       "is_removed": false,
       "created_at": "2026-03-22T17:10:00Z"
     }
   ]

**Pagination example**

.. code-block:: bash

   # First page
   GET /api/v1/feed?limit=20

   # Next page — pass the id of the last post from the previous response
   GET /api/v1/feed?limit=20&before_id=80
