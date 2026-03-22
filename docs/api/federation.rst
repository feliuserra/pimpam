Federation (ActivityPub)
========================

PimPam federates with the Fediverse using the
`ActivityPub <https://www.w3.org/TR/activitypub/>`_ protocol.
This allows PimPam users to follow and interact with accounts on
Mastodon, Pixelfed, Lemmy, and any other ActivityPub-compatible server.

All federation endpoints live at the **root level** (no ``/api/v1/`` prefix)
because the ActivityPub and WebFinger specifications define the paths.

.. note::

   Set ``DOMAIN`` in your ``.env`` to your public hostname (e.g. ``pimpam.social``)
   for federation to work. Federation can be disabled entirely with
   ``FEDERATION_ENABLED=false``.

----

Discovery
---------

WebFinger
~~~~~~~~~

.. code-block:: http

   GET /.well-known/webfinger?resource=acct:alice@pimpam.social

Used by remote servers to resolve ``@alice@pimpam.social`` to an AP actor URL.
Returns ``application/jrd+json``.

**Example response**

.. code-block:: json

   {
     "subject": "acct:alice@pimpam.social",
     "aliases": ["https://pimpam.social/users/alice"],
     "links": [
       {
         "rel": "self",
         "type": "application/activity+json",
         "href": "https://pimpam.social/users/alice"
       }
     ]
   }

NodeInfo
~~~~~~~~

.. code-block:: http

   GET /.well-known/nodeinfo
   GET /nodeinfo/2.1

Server capability and usage metadata. Makes PimPam visible to Fediverse
observer networks (e.g. instances.social).

----

Actor
-----

.. code-block:: http

   GET /users/{username}

Returns the AP Actor document for a local user. Must be requested with
``Accept: application/activity+json`` to receive JSON-LD (browsers are
redirected to the profile page).

**Example response**

.. code-block:: json

   {
     "@context": ["https://www.w3.org/ns/activitystreams", "https://w3id.org/security/v1"],
     "type": "Person",
     "id": "https://pimpam.social/users/alice",
     "preferredUsername": "alice",
     "name": "Alice",
     "inbox": "https://pimpam.social/users/alice/inbox",
     "outbox": "https://pimpam.social/users/alice/outbox",
     "publicKey": {
       "id": "https://pimpam.social/users/alice#main-key",
       "owner": "https://pimpam.social/users/alice",
       "publicKeyPem": "-----BEGIN PUBLIC KEY-----\n..."
     }
   }

----

Inbox
-----

.. code-block:: http

   POST /users/{username}/inbox

The primary entry point for incoming federation traffic.
All requests are verified against the sender's RSA public key
using HTTP Signatures (draft-cavage-http-signatures-12) before processing.
Returns ``202 Accepted`` for all signature-valid requests, including unknown activity types
(required by the AP spec).

**Handled activity types**

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Type
     - Behaviour
   * - ``Follow``
     - Creates a Follow record; immediately sends an ``Accept`` back to the sender
   * - ``Undo{Follow}``
     - Removes the Follow record
   * - ``Create{Note}``
     - Caches the remote post locally with its ``ap_id``
   * - ``Delete``
     - Removes the locally cached post matching the ``ap_id``
   * - ``Accept``
     - No-op for now (our outgoing Follow was accepted)

----

Outbox
------

.. code-block:: http

   GET /users/{username}/outbox

Returns an ``OrderedCollection`` of the user's 20 most recent local posts,
serialized as ``Create{Note}`` activities.

----

Followers / Following
---------------------

.. code-block:: http

   GET /users/{username}/followers
   GET /users/{username}/following

Return ``OrderedCollection`` documents listing follower and following actor IDs.

----

HTTP Signatures
---------------

All outgoing requests to remote inboxes are signed with the sender's RSA-2048
private key using the ``rsa-sha256`` algorithm. The signed headers are:
``(request-target)``, ``host``, ``date``, ``digest``.

All incoming inbox requests are verified the same way before any handler runs.

----

.. note::

   **Not yet implemented:** outgoing delivery triggered on post creation,
   federated follow initiation from a local user (the AP ``Follow`` activity send),
   ``Announce`` (boost/reblog), ``Like``. See :doc:`../missing`.
