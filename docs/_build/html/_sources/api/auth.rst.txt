Authentication
==============

Base path: ``/api/v1/auth``

All auth endpoints are rate-limited. Tokens use short-lived JWT access tokens (15 min)
paired with long-lived refresh tokens (30 days).

----

Register
--------

.. code-block:: http

   POST /api/v1/auth/register

Create a new local account. Usernames are lowercased and must be alphanumeric
(hyphens and underscores allowed). An RSA key pair is generated automatically
at registration for ActivityPub federation.

**Request body**

.. code-block:: json

   {
     "username": "alice",
     "email": "alice@example.com",
     "password": "supersecret",
     "display_name": "Alice"
   }

**Validation rules**

- ``username``: 3–50 chars, letters/numbers/hyphens/underscores only
- ``password``: minimum 8 characters
- ``email``: must be a valid email address

**Response** ``201 Created``

.. code-block:: json

   {
     "id": 1,
     "username": "alice",
     "display_name": "Alice",
     "bio": null,
     "avatar_url": null,
     "karma": 0,
     "created_at": "2026-03-22T17:00:00Z"
   }

**Errors**

- ``409`` — username or email already taken
- ``422`` — validation failure

----

Login
-----

.. code-block:: http

   POST /api/v1/auth/login

Authenticate with username and password. Returns a token pair.

**Request body**

.. code-block:: json

   {
     "username": "alice",
     "password": "supersecret"
   }

**Response** ``200 OK``

.. code-block:: json

   {
     "access_token": "<jwt>",
     "refresh_token": "<jwt>",
     "token_type": "bearer"
   }

**Errors**

- ``401`` — incorrect username or password

----

Refresh
-------

.. code-block:: http

   POST /api/v1/auth/refresh

Exchange a valid refresh token for a new access + refresh token pair.
Use this when the access token expires rather than asking the user to log in again.

**Request body**

.. code-block:: json

   {
     "refresh_token": "<jwt>"
   }

**Response** ``200 OK`` — same shape as login response.

**Errors**

- ``401`` — refresh token invalid or expired
