---
doc_id: migration-v2-to-v3-pagination
title: Pagination changes in v3
product: Nimbus API
doc_type: migration-guide
version: v3
status: current
source_url: https://docs.nimbus.example/migrate/v2-to-v3/pagination
last_updated: 2026-10-08
---

# Pagination changes in v3

v3 replaces page-based pagination with cursor pagination.

## Before: page and per_page

In v2 a client requested pages by number:

    GET /users?page=2&per_page=50

The response included `total_pages`. Deep pages became slow as the dataset grew.

## After: limit and cursor

In v3 a client requests a page size and an opaque cursor:

    GET /users?limit=50&cursor=Y3Vyc29yXzEy

The response returns `next_cursor`. Stop when `next_cursor` is `null`.

## Migration steps

1. Replace `per_page` with `limit`. The maximum is 100.
2. Store `next_cursor` from each response.
3. Pass it as `cursor` on the next request.
4. Remove any logic that depends on `total_pages`.

## Common mistakes

- Sending `page` to v3 returns `400 Bad Request`.
- Reusing a cursor after its 24-hour lifetime returns `410 Gone`.
- Changing filters between pages can skip or repeat records.
