Feed
====

Base path: ``/api/v1/feed``

Requires authentication.

----

Get chronological feed
-----------------------

.. code-block:: http

   GET /api/v1/feed

Returns posts from users you follow, ordered by time descending.
**There is no algorithmic ranking.** The order is always newest first, always.

Pagination is cursor-based via ``before_id`` — never offset-based,
which avoids the duplicate/missing post problems that come with ``OFFSET``.

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
       "title": "Hello from Alice",
       "content": "First post!",
       "url": null,
       "author_id": 1,
       "community_id": null,
       "karma": 0,
       "created_at": "2026-03-22T17:10:00Z"
     }
   ]

**Pagination example**

.. code-block:: bash

   # First page
   GET /api/v1/feed?limit=20

   # Next page — pass the id of the last post from the previous response
   GET /api/v1/feed?limit=20&before_id=80

.. warning::

   The feed will be empty until follow/unfollow is implemented.
   See :doc:`../missing`.
