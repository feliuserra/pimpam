Users & Profiles
================

Base path: ``/api/v1/users``

All write endpoints require a valid ``Authorization: Bearer <token>`` header.

----

Get own profile
---------------

.. code-block:: http

   GET /api/v1/users/me

Returns the authenticated user's full profile.

**Response** ``200 OK``

.. code-block:: json

   {
     "id": 1,
     "username": "alice",
     "display_name": "Alice",
     "bio": "Hello world",
     "avatar_url": null,
     "karma": 42,
     "created_at": "2026-03-22T17:00:00Z"
   }

----

Update own profile
------------------

.. code-block:: http

   PATCH /api/v1/users/me

Update editable profile fields. All fields are optional — only send what you want to change.

**Request body**

.. code-block:: json

   {
     "display_name": "Alice B.",
     "bio": "Building the open web.",
     "avatar_url": "https://example.com/avatar.jpg"
   }

**Response** ``200 OK`` — updated profile object.

----

Get public profile
------------------

.. code-block:: http

   GET /api/v1/users/{username}

Fetch any user's public profile by username. Works for both local and federated users.

**Response** ``200 OK`` — same shape as ``/me``.

**Errors**

- ``404`` — user not found

----

.. note::

   **Not yet implemented:** follow / unfollow endpoints.
   Until these exist, the feed will always be empty for new users.
   See :doc:`../missing` for the full list.
