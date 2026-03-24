Friend Groups
=============

Base path: ``/api/v1/friend-groups``

Requires authentication (verified account).

Friend groups let you curate lists of people you follow and post exclusively to them.
Every user gets a special **Close Friends** group (auto-created on first access) plus any
number of named groups they choose to create.

When you post with ``visibility: "group"`` and a ``friend_group_id``, only the group owner
and the group's members can see that post. Group posts are never indexed in search, never
federated to ActivityPub, and cannot be shared.

**Rules**

- You can only add people you already follow (pending follows are excluded).
- Members are notified when they are added or removed.
- Members can see the full member list.
- The Close Friends group cannot be renamed or deleted.
- Community posts must have ``visibility: "public"``.

----

Friend group object
-------------------

.. code-block:: json

   {
     "id": 1,
     "name": "Close Friends",
     "is_close_friends": true,
     "member_count": 3,
     "members": [
       {"user_id": 7, "username": "alice", "added_at": "2026-03-24T10:00:00Z"}
     ],
     "created_at": "2026-03-01T00:00:00Z"
   }

The ``members`` array is populated on detail endpoints (GET ``/{id}`` and ``/close-friends``).
The list endpoint (GET ``/``) returns ``members: []`` and a correct ``member_count``.

----

List groups
-----------

.. code-block:: text

   GET /api/v1/friend-groups

Return all friend groups you own, ordered with Close Friends first then by creation date.
Each group includes a ``member_count`` but an empty ``members`` list for efficiency.

**Response** ``200 OK`` — array of friend group objects.

----

Create a group
--------------

.. code-block:: text

   POST /api/v1/friend-groups

Create a new named friend group.

**Request body**

.. code-block:: json

   {"name": "Hiking crew"}

**Response** ``201 Created`` — the new group with full member list (empty at creation).

**Errors**

- ``422`` — name is empty or missing.

----

Get Close Friends group
-----------------------

.. code-block:: text

   GET /api/v1/friend-groups/close-friends

Return the Close Friends group, creating it automatically if it doesn't exist yet.
This is the group used when you post with ``visibility: "group"`` and want to target
your close friends.

**Response** ``200 OK`` — the Close Friends group with full member list.

----

Group detail
------------

.. code-block:: text

   GET /api/v1/friend-groups/{id}

Return a group with its full member list (``user_id``, ``username``, ``added_at``).

**Errors**

- ``404`` — group not found or you are not the owner.

----

Rename a group
--------------

.. code-block:: text

   PATCH /api/v1/friend-groups/{id}

Rename a friend group.

**Request body**

.. code-block:: json

   {"name": "New name"}

**Response** ``200 OK`` — the updated group with full member list.

**Errors**

- ``400`` — attempting to rename the Close Friends group.
- ``404`` — group not found or you are not the owner.
- ``422`` — name is empty or missing.

----

Delete a group
--------------

.. code-block:: text

   DELETE /api/v1/friend-groups/{id}

Delete a friend group and all its membership records. Posts previously shared with this
group become inaccessible to members (they remain stored but the group no longer exists).

**Response** ``204 No Content``

**Errors**

- ``400`` — attempting to delete the Close Friends group.
- ``404`` — group not found or you are not the owner.

----

Add a member
------------

.. code-block:: text

   POST /api/v1/friend-groups/{id}/members

Add a user to the group. You must be following them. The added user receives a
``friend_group_added`` notification.

**Request body**

.. code-block:: json

   {"user_id": 42}

**Response** ``201 Created`` — the updated group with full member list.

**Errors**

- ``400`` — you don't follow this user, or you tried to add yourself.
- ``404`` — group not found or you are not the owner.
- ``409`` — user is already a member.

----

Remove a member
---------------

.. code-block:: text

   DELETE /api/v1/friend-groups/{id}/members/{user_id}

Remove a user from the group. The removed user receives a ``friend_group_removed``
notification.

**Response** ``204 No Content``

**Errors**

- ``404`` — group not found, you are not the owner, or user is not a member.

----

Post visibility
---------------

When creating a post, supply ``visibility`` and (for group posts) ``friend_group_id``:

.. code-block:: json

   {
     "title": "Weekend photos",
     "content": "Had a great hike!",
     "visibility": "group",
     "friend_group_id": 1
   }

- ``"public"`` (default) — visible to everyone, indexed, federated.
- ``"group"`` — visible only to the group owner and current members; not indexed, not federated, not shareable.

Community posts (``community_id`` set) must use ``visibility: "public"``.
