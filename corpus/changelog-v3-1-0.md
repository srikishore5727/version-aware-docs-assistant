---
doc_id: changelog-v3-1-0
title: v3.1.0 release notes
product: Nimbus API
doc_type: changelog
version: v3
status: current
source_url: https://docs.nimbus.example/changelog/v3-1-0
last_updated: 2026-10-20
---

# v3.1.0 release notes

Released 20 October 2026. No breaking changes.

## Added

- `role` filter on `GET /users`.
- `last_login_at` on the user object.
- Webhook retries now use exponential backoff for up to 24 hours.

## Fixed

- `next_cursor` was occasionally empty on the final page. It now returns `null`.
- `409 Conflict` messages now include the conflicting email address.

## Deprecated

- Nothing in this release.

## Upgrade

This release is backward compatible with v3.0.0. No client changes are required.
