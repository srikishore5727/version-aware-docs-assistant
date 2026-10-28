---
doc_id: changelog-v1-5-0
title: v1.5.0 release notes
product: Nimbus API
doc_type: changelog
version: v1
status: superseded
source_url: https://docs.nimbus.example/changelog/v1-5-0
last_updated: 2025-01-22
---

# v1.5.0 release notes

Released 22 January 2025. Superseded by v2 and v3.

## Added

- Webhook delivery retries, up to three attempts.
- `created_at` on the user object.
- A `per_page` maximum of 100.

## Fixed

- Duplicate webhook deliveries when a request timed out after a successful write.
- `user_name` accepted leading and trailing whitespace.

## Deprecated

- The `api_key` query parameter. It was removed in v3.
- `page`-based pagination. It was removed in v3.

## Notes

v1 is no longer supported. New integrations should start on v3.
