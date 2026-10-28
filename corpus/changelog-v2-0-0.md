---
doc_id: changelog-v2-0-0
title: v2.0.0 release notes
product: Nimbus API
doc_type: changelog
version: v2
status: superseded
source_url: https://docs.nimbus.example/changelog/v2-0-0
last_updated: 2025-06-15
---

# v2.0.0 release notes

Released 15 June 2025. Superseded by v3.

## Added

- Bearer token authentication. The `api_key` query parameter is deprecated.
- `page` and `per_page` query parameters on list endpoints.
- `X-Nimbus-Signature` on webhook deliveries.
- `role` field on the user object.

## Changed

- Error responses now use a consistent `{ "error": { "code", "message" } }` shape.

## Removed

- The legacy `/v1/users/create` endpoint. Use `POST /users`.

## Upgrade

Follow the v1 to v2 migration guide.
