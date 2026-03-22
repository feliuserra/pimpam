Direct Messages
===============

Base path: ``/api/v1/messages``

Requires authentication.

.. important::

   Messages are **end-to-end encrypted**. The server stores only ciphertext —
   it never sees the plaintext content of any message. Encryption and decryption
   must happen entirely on the client side before calling these endpoints.

   The ``encrypted_key`` field carries the AES symmetric key, itself encrypted
   with the recipient's RSA public key, so only the recipient can decrypt the message.

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

----

Get conversation
----------------

.. code-block:: http

   GET /api/v1/messages/{other_user_id}

Retrieve the message thread between you and another user, newest first.
Returns up to 50 messages.

**Response** ``200 OK`` — array of message objects (same shape as above).

----

.. note::

   **Not yet implemented:** client-side encryption library integration,
   marking messages as read, listing all conversations (inbox view),
   deleting messages, read receipts. See :doc:`../missing`.
