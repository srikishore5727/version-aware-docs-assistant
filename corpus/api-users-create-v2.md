---
doc_id: api-users-create-v2
title: Create user (v2)
product: Nimbus API
doc_type: api-reference
version: v2
status: superseded
source_url: https://docs.nimbus.example/v2/users/create
last_updated: 2025-06-18
---

# Create user

This page describes v2. It is superseded by the v3 API reference.

## Request body

| Field | Type | Required | Notes |
|---|---|---|---|
| `user_name` | string | Yes | Renamed to `display_name` in v3 |
| `email` | string | Yes | Must be unique |
| `role` | string | No | Defaults to `member` |

## Response

Returns `200 OK` with the created user.

## Notes

In v2 the field is `user_name`. Sending `display_name` to v2 is ignored.
v3 reverses this: `display_name` is required and `user_name` is rejected.
