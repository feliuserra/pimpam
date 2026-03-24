Design Principles
=================

These are the non-negotiable rules that define what PimPam is.
Every architectural and product decision should be evaluated against them.

----

No algorithmic ranking
-----------------------

Feeds are always chronological. Posts are never reordered by engagement,
predicted interest, or any machine learning model. The feed query sorts
by ``created_at DESC`` and that is the only ordering that will ever be used.

No ads, no tracking
-------------------

PimPam collects the minimum data needed to operate. There are no tracking
pixels, no behavioral analytics, no fingerprinting, no third-party data sharing.
GDPR rights (access, erasure, portability, restriction) must be implementable
at any point — design data models with this in mind.

Privacy by design
-----------------

Direct messages are end-to-end encrypted. The server stores only ciphertext.
Encryption keys never leave the client. The server must never be in a position
to read message content, even under legal compulsion.

Federation (ActivityPub)
------------------------

PimPam is part of the Fediverse. Users can follow and be followed by accounts
on Mastodon, Pixelfed, Lemmy, and any other AP-compatible server. Federation
is a first-class feature, not an afterthought. All outgoing requests are signed
with RSA-2048 HTTP Signatures. All incoming requests are verified before processing.

AGPL-3.0
---------

All code is AGPL-3.0. Modified versions run as a network service must make
their source available. Never introduce dependencies that conflict with this license.

Simplicity first
----------------

Build the minimum that works correctly and securely. Do not add features,
abstractions, or configurability that are not needed right now. Three similar
lines of code are better than a premature abstraction.

Transparent moderation
-----------------------

Moderation is community-elected, transparent, and appealable. No shadow banning.
No opaque automated removal. Every moderation action must be visible and contestable
by the affected user.
