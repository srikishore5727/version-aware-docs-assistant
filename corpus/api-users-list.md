---
doc_id: api-users-list
title: List users
product: Nimbus API
doc_type: api-reference
version: v3
status: current
source_url: https://docs.nimbus.example/v3/users/list
last_updated: 2026-10-12
---

# List users

`GET /users` returns a paginated list of users in the current workspace.

## Query parameters

| Parameter | Type | Default | Notes |
|---|---|---|---|
| `limit` | integer | 20 | Maximum 100 |
| `cursor` | string | none | Opaque cursor from the previous response |
| `role` | string | none | Filter by role. Added in v3.1.0 |

## Pagination

v3 uses cursor pagination. The response contains `next_cursor`; pass it as
`cursor` to fetch the next page. The `page` and `per_page` parameters were
removed in v3 and now return a `400 Bad Request` error.

## Response

    {
      "data": [
        { "id": "usr_01H9", "display_name": "Ada Lovelace", "role": "member" }
      ],
      "next_cursor": "Y3Vyc29yXzEy"
    }

## Errors

- `400 Bad Request` when `page` or `per_page` is supplied
- `401 Unauthorized` when the bearer token is missing or expired
