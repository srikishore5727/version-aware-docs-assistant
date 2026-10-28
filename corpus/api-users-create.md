---
doc_id: api-users-create
title: Create user
product: Nimbus API
doc_type: api-reference
version: v3
status: current
source_url: https://docs.nimbus.example/v3/users/create
last_updated: 2026-10-12
---

# Create user

`POST /users` creates a user in the current workspace. The caller must have the `users:write` scope.

## Request body

| Field | Type | Required | Notes |
|---|---|---|---|
| `display_name` | string | Yes | Replaces `user_name`, which was removed in v3 |
| `email` | string | Yes | Must be unique within the workspace |
| `role` | string | No | One of `admin`, `member`, or `viewer`. Defaults to `member` |

## Response

Returns `201 Created` with the user object:

    {
      "id": "usr_01H9",
      "display_name": "Ada Lovelace",
      "email": "ada@example.com",
      "role": "member"
    }

## Errors

- `422 Unprocessable Entity` when the request body still contains `user_name`
- `409 Conflict` when the email already exists
- `403 Forbidden` when the token lacks the `users:write` scope

## Notes

Requests that send `user_name` are rejected. Follow the v2 to v3 migration guide
to rename the field before upgrading.
