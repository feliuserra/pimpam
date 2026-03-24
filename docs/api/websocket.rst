WebSocket
=========

Endpoint: ``WS /ws``

Real-time event stream for the authenticated user, backed by Redis pub/sub.
One persistent connection per user; each message is pushed as a JSON text frame.

**Authentication:** pass a valid JWT access token as a query parameter:

.. code-block:: text

   ws://localhost:8000/ws?token=<access_token>

The connection is closed with code ``1008`` (Policy Violation) if the token is
missing or invalid. The connection closes automatically after **60 seconds of client
silence** (no frames sent). Clients should reconnect; there is no message replay on
reconnect.

Redis being down never prevents primary operations — WS events are best-effort.

----

Events pushed to the client
----------------------------

All events share the envelope ``{"type": "<event>", "data": {...}}``.

new_post
~~~~~~~~

A user you follow published or reshared a post.

.. code-block:: json

   {
     "type": "new_post",
     "data": {"id": 7, "title": "Hello world", "author": "alice"}
   }

new_comment
~~~~~~~~~~~

A comment was posted on a thread you are watching (post author or anyone who has
previously commented on the post), excluding your own comments.

.. code-block:: json

   {
     "type": "new_comment",
     "data": {
       "post_id": 42,
       "comment_id": 101,
       "author": "bob",
       "parent_id": null
     }
   }

new_message
~~~~~~~~~~~

A direct message was received.

.. code-block:: json

   {
     "type": "new_message",
     "data": {"sender_id": 3, "sender_username": "carol"}
   }

karma_update
~~~~~~~~~~~~

One of your posts was voted on.

.. code-block:: json

   {
     "type": "karma_update",
     "data": {"post_id": 7, "post_karma": 14, "user_karma": 82}
   }

notification
~~~~~~~~~~~~

A new notification was stored in your inbox (see :doc:`notifications`).

.. code-block:: json

   {
     "type": "notification",
     "data": {"id": 55, "type": "vote", "group_count": 3, "is_read": false}
   }

typing
~~~~~~

Another user is typing a direct message to you.

.. code-block:: json

   {
     "type": "typing",
     "data": {"sender_id": 3, "sender_username": "carol"}
   }

----

Events sent from the client
-----------------------------

Clients may send JSON text frames to trigger server-side actions. Unknown frame
types are silently ignored. Any frame (including plain heartbeats) resets the 60 s
idle timeout.

typing
~~~~~~

Forward a typing indicator to a DM recipient.

.. code-block:: json

   {"type": "typing", "recipient_id": 3}

The server immediately publishes a ``typing`` event to the recipient's channel.
Malformed frames (invalid JSON, missing ``recipient_id``) are silently discarded.
