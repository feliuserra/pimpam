Search
======

Base path: ``/api/v1/search``

Full-text search powered by `Meilisearch <https://www.meilisearch.com>`_.
No authentication required.

Returns ``503`` if ``SEARCH_ENABLED=false`` or Meilisearch is unreachable.

.. note::

   Three indexes are maintained: ``posts``, ``users``, and ``communities``.
   All are updated automatically (fire-and-forget) on create, edit, and delete.

----

Search
------

.. code-block:: text

   GET /api/v1/search

**Query parameters**

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Parameter
     - Description
   * - ``q``
     - **Required.** Search query (minimum 1 character).
   * - ``type``
     - Restrict results to ``post``, ``user``, or ``community``. Omit to search all three.
   * - ``community``
     - Restrict post results to a single community (by name). Ignored when ``type`` is not ``post``.
   * - ``limit``
     - Results per page (default: 20, max: 100).
   * - ``offset``
     - Pagination offset (default: 0).

**Response** ``200 OK``

.. code-block:: json

   {
     "query": "open source",
     "total": 42,
     "hits": [
       {
         "type": "post",
         "id": 7,
         "title": "Open source governance",
         "content": "How communities self-govern...",
         "url": null,
         "image_url": null,
         "author_id": 3,
         "community_id": 1,
         "karma": 28,
         "created_at": "2026-03-20T09:00:00Z"
       },
       {
         "type": "user",
         "id": 5,
         "username": "alice",
         "display_name": "Alice",
         "bio": "Open source contributor",
         "avatar_url": null,
         "karma": 120
       },
       {
         "type": "community",
         "id": 2,
         "name": "opensource",
         "description": "Everything open source",
         "member_count": 340,
         "created_at": "2026-01-01T00:00:00Z"
       }
     ]
   }

Results are ranked by relevance. Removed posts are never returned.
When ``type`` is omitted, results from all three indexes are merged in a single response.

**Errors**

- ``404`` — community specified in ``?community=`` not found
- ``503`` — search is disabled or Meilisearch is unreachable
