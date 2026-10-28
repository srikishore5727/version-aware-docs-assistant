---
doc_id: migration-v2-to-v3
title: Migrate from v2 to v3
product: Nimbus API
doc_type: migration-guide
version: v3
status: current
source_url: https://docs.nimbus.example/migrate/v2-to-v3
last_updated: 2026-10-08
---

# Migrate from v2 to v3

v3 contains three breaking changes. Most integrations can be upgraded in under an hour.

## 1. Rename user_name to display_name

In every request body, rename `user_name` to `display_name`. The v3 API rejects
the old field with `422 Unprocessable Entity`.

Before:

    { "user_name": "Ada Lovelace" }

After:

    { "display_name": "Ada Lovelace" }

## 2. Replace page with cursor

`page` and `per_page` are removed. Use `limit` and `cursor` instead. The response
now returns `next_cursor` rather than a total page count.

## 3. Expect 201 instead of 200

`POST /users` now returns `201 Created`. Update any client that checks for
exactly `200`.

## Checklist

- [ ] Rename every `user_name` field
- [ ] Replace page-based pagination
- [ ] Accept `201` from create endpoints
- [ ] Re-run integration tests against v3
