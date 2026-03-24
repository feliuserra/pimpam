Media Uploads
=============

Base path: ``/api/v1/media``

Requires authentication (verified account).

Images are processed server-side before storage: converted to WebP, EXIF metadata
stripped, and resized. The returned URL is then passed to other endpoints
(``PATCH /users/me`` for avatars, ``POST /posts`` for post images).

Returns ``503`` if ``STORAGE_ENABLED=false`` or the storage backend is unreachable.

.. note::

   Rate limit: ``POST /media/upload`` — 10/minute.

   Storage backend: S3-compatible (MinIO in development, Cloudflare R2 in production).
   Configure via ``STORAGE_*`` environment variables.

----

Upload an image
---------------

.. code-block:: text

   POST /api/v1/media/upload

Upload a single image file. The server validates the file content (not just the
Content-Type header), converts it to WebP, strips all metadata, and uploads it to
S3-compatible storage.

**Request**

Multipart form upload with the following fields:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Field
     - Description
   * - ``file``
     - The image file. Accepted formats: JPEG, PNG, WebP, GIF. Maximum size: 10 MB.
   * - ``media_type``
     - ``avatar`` or ``post_image``.

**Processing rules by media_type:**

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Type
     - Processing
   * - ``avatar``
     - Resized to 512 × 512 px (center-cropped to square), converted to WebP.
   * - ``post_image``
     - Longest side capped at 2000 px (aspect ratio preserved), converted to WebP.

**Response** ``201 Created``

.. code-block:: json

   {"url": "https://cdn.example.com/pimpam/abc123.webp"}

Use this URL in subsequent requests:

- Avatar: ``PATCH /api/v1/users/me`` → ``{"avatar_url": "<url>"}``
- Post image: ``POST /api/v1/posts`` → ``{"image_url": "<url>", ...}``

**Errors**

- ``422`` — unsupported file format, file is corrupt, or invalid ``media_type``
- ``502`` — storage backend is unavailable
- ``503`` — storage is disabled on this server
