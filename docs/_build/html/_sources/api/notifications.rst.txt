Notifications
=============

Base path: ``/api/v1/notifications``

Requires authentication (verified account).

The notification inbox stores events for things that happen on the platform while you
are offline. Events are also delivered in real time over the WebSocket connection when
you are online. Failure of either delivery path never blocks the underlying operation.

**14 notification types:**

.. list-table::
   :header-rows: 1
   :widths: 25 10 65

   * - Type
     - Grouped
     - Trigger
   * - ``reply``
     - no
     - Someone replied to one of your comments
   * - ``reaction``
     - yes
     - Someone reacted to one of your comments
   * - ``new_comment``
     - yes
     - Someone commented on one of your posts
   * - ``share``
     - no
     - Someone shared one of your posts
   * - ``follow``
     - no
     - Someone followed you
   * - ``vote``
     - yes
     - Someone voted on one of your posts
   * - ``post_removed``
     - no
     - A moderator removed one of your posts
   * - ``comment_removed``
     - no
     - A moderator removed one of your comments
   * - ``ban_proposed``
     - no
     - A ban was proposed against you in a community
   * - ``banned``
     - no
     - You were banned from a community
   * - ``appeal_resolved``
     - no
     - Your ban appeal was resolved
   * - ``mod_nominated``
     - no
     - You were nominated for a moderator role
   * - ``mod_promoted``
     - no
     - You were promoted to a moderator role
   * - ``ownership_offered``
     - no
     - You were offered ownership of a community

**Grouping:** Grouped types (``reaction``, ``vote``, ``new_comment``) upsert into a
single unread row per ``group_key``, incrementing ``group_count``. Marking the
grouped notification as read closes the group; the next event of the same type starts
a fresh row. Clients should render ``>99`` when ``group_count > 99``.

**Preferences:** All types are enabled by default. An opt-out row is written only when
a type is disabled — no rows means everything is on.

----

Notification object
-------------------

.. code-block:: json

   {
     "id": 1,
     "user_id": 5,
     "type": "vote",
     "actor_id": 3,
     "post_id": 42,
     "comment_id": null,
     "community_id": null,
     "group_key": "vote:post:42",
     "group_count": 7,
     "is_read": false,
     "created_at": "2026-03-24T10:00:00Z"
   }

----

Inbox
-----

.. code-block:: text

   GET /api/v1/notifications

Return the authenticated user's notification inbox. Unread notifications appear first,
then read ones, both ordered newest-first within each group.

**Query parameters**

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Parameter
     - Description
   * - ``limit``
     - Maximum number of results to return (default: 20).
   * - ``before_id``
     - Cursor for pagination — return notifications with ``id < before_id``.

**Response** ``200 OK`` — array of notification objects.

----

Unread count
------------

.. code-block:: text

   GET /api/v1/notifications/unread-count

Return the number of unread notifications for the current user.
Intended for badge counters in the UI.

**Response** ``200 OK``

.. code-block:: json

   {"count": 4}

----

Mark one as read
----------------

.. code-block:: text

   PATCH /api/v1/notifications/{id}/read

Mark a single notification as read. For grouped notifications, this closes the group —
the next event of the same type will start a fresh row with ``group_count = 1``.

**Response** ``200 OK`` — the updated notification object.

**Errors**

- ``404`` — notification not found or does not belong to you.

----

Mark all as read
----------------

.. code-block:: text

   PATCH /api/v1/notifications/read-all

Mark all unread notifications as read at once.

**Response** ``200 OK``

.. code-block:: json

   {"updated": 12}

----

List preference overrides
-------------------------

.. code-block:: text

   GET /api/v1/notifications/preferences

Return the list of notification types that the current user has **disabled**.
An empty list means all types are enabled (the default).

**Response** ``200 OK``

.. code-block:: json

   ["vote", "reaction"]

----

Update a preference
-------------------

.. code-block:: text

   PATCH /api/v1/notifications/preferences

Enable or disable a notification type.

**Request body**

.. code-block:: json

   {"notification_type": "vote", "enabled": false}

**Response** ``200 OK``

.. code-block:: json

   {"notification_type": "vote", "enabled": false}

**Errors**

- ``400`` — unknown notification type.

----

Real-time delivery
------------------

Every notification is also pushed over the WebSocket connection (``WS /ws?token=<jwt>``)
as a ``notification`` event if the user is currently connected:

.. code-block:: json

   {
     "type": "notification",
     "data": {
       "id": 1,
       "type": "vote",
       "group_count": 7,
       "is_read": false
     }
   }

Redis being down never prevents the notification from being stored.
