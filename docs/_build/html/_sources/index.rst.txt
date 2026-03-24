PimPam API Documentation
========================

**PimPam** is an open-source, ad-free, human-first social network.
No algorithms. No ads. No owners. Licensed under AGPL-3.0.

The backend is a `FastAPI <https://fastapi.tiangolo.com>`_ application exposing a
versioned REST API (``/api/v1/``) and a set of
`ActivityPub <https://www.w3.org/TR/activitypub/>`_ federation endpoints at the root level.

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api/auth
   api/users
   api/feed
   api/posts
   api/comments
   api/communities
   api/moderation
   api/messages
   api/notifications
   api/friend_groups
   api/search
   api/media
   api/websocket
   api/federation

.. toctree::
   :maxdepth: 1
   :caption: Project

   missing
   principles

----

Quick links
-----------

- **Interactive docs (Swagger UI):** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **Health check:** ``GET /health``
- **Source code:** https://github.com/feliuserra/pimpam
