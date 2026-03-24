Stories
=======

Base path: ``/api/v1/stories``

Requires authentication on all endpoints.

.. note::

   **Privacy constraints (by design):**

   - No "seen by" list — viewing a story is never recorded.
   - No ``expires_at`` in API responses — prevents countdown UI on the frontend.
   - Reported stories are soft-deleted and retained 48 h for moderator review before permanent deletion.
   - Expired, non-reported stories are hard-deleted by an hourly background task.

----

Create a story
--------------

.. code-block:: http

   POST /api/v1/stories

Rate limit: ``20/hour``.

The image must already be uploaded via ``POST /media/upload`` before calling this endpoint.

**Request body**

.. code-block:: json

   {
     "image_url": "https://cdn.example.com/img.webp",
     "caption": "Hello world",
     "duration_hours": 24
   }

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Field
     - Required
     - Description
   * - ``image_url``
     - Yes
     - URL of the uploaded image (max 500 chars).
   * - ``caption``
     - No
     - Optional caption (max 200 chars).
   * - ``duration_hours``
     - No
     - How long the story lives. Must be one of ``12``, ``24``, ``48``, ``168`` (7 days). Defaults to ``24``. Invalid values silently fall back to ``24``.

**Response** ``201 Created``

.. code-block:: json

   {
     "id": 1,
     "author_id": 42,
     "author_username": "alice",
     "author_avatar_url": "https://cdn.example.com/avatar.webp",
     "image_url": "https://cdn.example.com/img.webp",
     "caption": "Hello world",
     "created_at": "2026-03-24T10:00:00Z"
   }

.. note::

   ``expires_at`` is intentionally absent from the response.

----

Stories feed
------------

.. code-block:: http

   GET /api/v1/stories/feed

Rate limit: ``60/minute``.

Returns active (non-expired, non-removed) stories from:

- Users you follow (accepted follows only — pending federated follows excluded)
- Members of communities you have joined

Your own stories are excluded from this feed (shown separately on the profile/compose flow).
Results are ordered newest first.

**Query parameters**

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Parameter
     - Default
     - Description
   * - ``limit``
     - ``50``
     - Maximum number of stories to return. Hard cap: ``100``.

**Response** ``200 OK``

.. code-block:: json

   [
     {
       "id": 1,
       "author_id": 42,
       "author_username": "alice",
       "author_avatar_url": "https://cdn.example.com/avatar.webp",
       "image_url": "https://cdn.example.com/img.webp",
       "caption": "Morning coffee",
       "created_at": "2026-03-24T08:00:00Z"
     }
   ]

----

Delete a story
--------------

.. code-block:: http

   DELETE /api/v1/stories/{story_id}

Delete your own story before it expires. Authors only — other users receive ``403``.

**Response** ``204 No Content``

**Error responses**

.. list-table::
   :header-rows: 1
   :widths: 15 85

   * - Status
     - Meaning
   * - ``403 Forbidden``
     - The story belongs to another user.
   * - ``404 Not Found``
     - Story does not exist.

----

Report a story
--------------

.. code-block:: http

   POST /api/v1/stories/{story_id}/report

Rate limit: ``10/minute``.

Reports a story for moderator review. The story is immediately soft-deleted (``is_removed = true``) and hidden from all viewers. The database row is retained for 48 h so moderators can review the content before it is permanently deleted.

Attempting to report an already-removed story returns ``404``.

**Response** ``204 No Content``

**Error responses**

.. list-table::
   :header-rows: 1
   :widths: 15 85

   * - Status
     - Meaning
   * - ``404 Not Found``
     - Story does not exist or has already been removed.
