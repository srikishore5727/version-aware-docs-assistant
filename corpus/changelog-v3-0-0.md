---
doc_id: changelog-v3-0-0
title: v3.0.0 release notes
product: Nimbus API
doc_type: changelog
version: v3
status: current
source_url: https://docs.nimbus.example/changelog/v3-0-0
last_updated: 2026-10-01
---

# v3.0.0 release notes

Released 1 October 2026. This is a breaking release.

## Removed

- `user_name` on the user object. Use `display_name` instead.
- `page` and `per_page` query parameters on list endpoints.
- The `api_key` query parameter. It was deprecated in v2 and is now rejected.

## Changed

- `POST /users` returns `201 Created` instead of `200 OK`.
- List responses return `next_cursor` instead of `total_pages`.

## Added

- `limit` and `cursor` query parameters for pagination.
- `display_name` is now required when creating a user.

## Upgrade

Follow the v2 to v3 migration guide. Most integrations take under an hour.
