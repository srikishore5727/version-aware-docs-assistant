---
doc_id: api-auth-tokens
title: Authentication
product: Nimbus API
doc_type: api-reference
version: v3
status: current
source_url: https://docs.nimbus.example/v3/auth
last_updated: 2026-10-02
---

# Authentication

All Nimbus API requests use a bearer token in the `Authorization` header:

    Authorization: Bearer <token>

## Getting a token

`POST /auth/token` with `client_id` and `client_secret` returns an access token
and its expiry time.

## Expiry

Access tokens expire after 60 minutes. Expired tokens return `401 Unauthorized`.

## Refreshing

`POST /auth/refresh` exchanges a valid refresh token for a new access token.
Refresh tokens are valid for 30 days.

## Scopes

Tokens carry scopes such as `users:read` and `users:write`. A missing scope
returns `403 Forbidden`.

## Migration note

v1 accepted an `api_key` query parameter. That mechanism was removed in v2.
See the v1 to v2 authentication guide.
