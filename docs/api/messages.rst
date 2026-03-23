Direct Messages
===============

Base path: ``/api/v1/messages``

Requires authentication.

.. important::

   Messages are **end-to-end encrypted**. The server stores only ciphertext —
   it never sees the plaintext content of any message. Encryption and decryption
   must happen entirely on the client side before calling these endpoints.

   The ``encrypted_key`` field carries the AES symmetric key, itself encrypted
   with the recipient's RSA public key, so only the recipient can decrypt it.

.. note::

   Rate limit: ``POST /messages`` — 20/min.

----

Send a message
--------------

.. code-block:: http

   POST /api/v1/messages

Send an E2EE message to another user.

**Request body**

.. code-block:: json

   {
     "recipient_id": 2,
     "ciphertext": "<base64-encoded encrypted content>",
     "encrypted_key": "<base64-encoded AES key encrypted with recipient public key>"
   }

**Response** ``201 Created``

.. code-block:: json

   {
     "id": 1,
     "sender_id": 1,
     "recipient_id": 2,
     "ciphertext": "<base64>",
     "encrypted_key": "<base64>",
     "is_read": false,
     "created_at": "2026-03-22T17:00:00Z"
   }

**Errors**

- ``400`` — cannot send a message to yourself
- ``404`` — recipient not found

----

Inbox
-----

.. code-block:: http

   GET /api/v1/messages

List all conversations for the authenticated user. Returns one summary per
conversation partner, ordered by most recent message first.

**Response** ``200 OK``

.. code-block:: json

   [
     {
       "other_user_id": 2,
       "other_username": "bob",
       "last_message_at": "2026-03-22T17:05:00Z",
       "unread_count": 3
     }
   ]

.. list-table:: ConversationSummary fields
   :header-rows: 1
   :widths: 25 75

   * - Field
     - Description
   * - ``other_user_id``
     - ID of the other participant in the conversation.
   * - ``other_username``
     - Username of the other participant.
   * - ``last_message_at``
     - Timestamp of the most recent message in the thread.
   * - ``unread_count``
     - Number of messages sent to you in this thread that you have not yet read.

----

Get conversation
----------------

.. code-block:: http

   GET /api/v1/messages/{other_user_id}

Retrieve the full message thread between you and another user, newest first.
Returns up to 50 messages.

**Response** ``200 OK`` — array of message objects (same shape as send response).

----

Mark as read
------------

.. code-block:: http

   PATCH /api/v1/messages/{other_user_id}/read

Mark all messages **from** ``other_user_id`` **to** the current user as read.
Call this when the user opens a conversation thread.

**Response** ``204 No Content``

----

.. note::

   **Not yet implemented:** client-side encryption library integration in the
   React frontend, deleting messages. See :doc:`../missing`.
