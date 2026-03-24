Users & Profiles
================

Base path: ``/api/v1/users``

Write endpoints require authentication. Read endpoints are public.

.. note::

   Rate limits: ``POST /users/{username}/follow`` — 20/min.

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

Update editable profile fields. All fields are optional.

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

Fetch any user's public profile by username.

**Response** ``200 OK`` — same shape as ``/me``.

**Errors**

- ``404`` — user not found

----

Follow a user
-------------

.. code-block:: http

   POST /api/v1/users/{username}/follow

Follow a user. Their posts will appear in your chronological feed.
Following remote (federated) users stores the follow locally — outgoing
AP ``Follow`` activity delivery is not yet implemented.

**Response** ``204 No Content``

**Errors**

- ``400`` — cannot follow yourself
- ``404`` — user not found
- ``409`` — already following this user

----

Unfollow a user
---------------

.. code-block:: http

   DELETE /api/v1/users/{username}/follow

Stop following a user. Their posts will no longer appear in your feed.

**Response** ``204 No Content``

**Errors**

- ``404`` — user not found, or you are not following them
