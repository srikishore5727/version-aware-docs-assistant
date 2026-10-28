---
doc_id: migration-v1-to-v2-auth
title: Authentication changes in v2
product: Nimbus API
doc_type: migration-guide
version: v2
status: superseded
source_url: https://docs.nimbus.example/migrate/v1-to-v2/auth
last_updated: 2025-06-20
---

# Authentication changes in v2

v2 replaced query-string API keys with bearer tokens.

## v1: api_key query parameter

In v1 every request carried the key in the URL:

    GET /users?api_key=sk_live_123

Keys in URLs leak through logs, browser history, and proxies.

## v2: Authorization header

In v2 the key is exchanged for a short-lived token:

    Authorization: Bearer <token>

Tokens are issued by `POST /auth/token` and expire after 60 minutes.

## Rotation

Rotate client secrets every 90 days. Revoking a client secret invalidates all
tokens issued from it.

## Common mistakes

- Keeping `api_key` in the query string alongside the header. v2 rejects it.
- Hard-coding tokens instead of refreshing them.
