Communities
===========

Base path: ``/api/v1/communities``

Write endpoints require authentication. Read endpoints are public.

.. note::

   Rate limits: ``POST /communities`` — 5/min.

----

List communities
----------------

.. code-block:: http

   GET /api/v1/communities

List all communities with page-based pagination.

**Query parameters**

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Parameter
     - Default
     - Description
   * - ``sort``
     - ``popular``
     - ``popular`` (most members first) · ``alphabetical`` · ``newest``
   * - ``page``
     - ``1``
     - Page number (1-indexed).
   * - ``limit``
     - ``20``
     - Results per page. Maximum ``50``.

**Response** ``200 OK`` — array of community objects.

----

Create a community
------------------

.. code-block:: http

   POST /api/v1/communities

Create a new community. The creator automatically becomes its owner
and first moderator, and is added as a member.

**Request body**

.. code-block:: json

   {
     "name": "python",
     "description": "Everything Python"
   }

**Response** ``201 Created``

.. code-block:: json

   {
     "id": 1,
     "name": "python",
     "description": "Everything Python",
     "owner_id": 1,
     "member_count": 1,
     "created_at": "2026-03-22T17:00:00Z"
   }

**Errors**

- ``409`` — community name already taken

----

Get a community
---------------

.. code-block:: http

   GET /api/v1/communities/{name}

Fetch a community by name.

**Errors**

- ``404`` — community not found

----

List community posts
--------------------

.. code-block:: http

   GET /api/v1/communities/{name}/posts

Chronological posts for a community, newest first. Cursor-paginated via ``before_id``.

Removed posts are hidden from public requests. Moderators of the community
(authenticated) see removed posts with ``"is_removed": true``.

**Query parameters**

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Parameter
     - Default
     - Description
   * - ``limit``
     - ``20``
     - Maximum posts to return. Maximum ``50``.
   * - ``before_id``
     - —
     - Return posts older than this post ID. Omit for the first page.

**Response** ``200 OK`` — array of post objects (see :doc:`posts`).

**Errors**

- ``404`` — community not found

----

Join a community
----------------

.. code-block:: http

   POST /api/v1/communities/{name}/join

Join a community as a member. Increments ``member_count``.

**Response** ``204 No Content``

----

Leave a community
-----------------

.. code-block:: http

   POST /api/v1/communities/{name}/leave

Leave a community. Decrements ``member_count``. Owners cannot leave
without transferring ownership first (not yet implemented).

**Response** ``204 No Content``

----

Moderation
----------

See :doc:`moderation` for the full moderation API:
post removal and restore, ban proposals, and moderator promotion.
