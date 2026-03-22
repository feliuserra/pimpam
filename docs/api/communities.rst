Communities
===========

Base path: ``/api/v1/communities``

Write endpoints require authentication.

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

**Validation rules**

- ``name``: 3–100 chars, letters/numbers/hyphens/underscores only, lowercased automatically

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

.. note::

   **Not yet implemented:** listing all communities, listing posts within a community,
   community moderation tools (ban, remove post), ownership transfer.
   See :doc:`../missing`.
