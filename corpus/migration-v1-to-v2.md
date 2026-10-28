---
doc_id: migration-v1-to-v2
title: Migrate from v1 to v2
product: Nimbus API
doc_type: migration-guide
version: v2
status: superseded
source_url: https://docs.nimbus.example/migrate/v1-to-v2
last_updated: 2025-06-20
---

# Migrate from v1 to v2

This guide covers the v1 to v2 upgrade. It is superseded by later migration guides.

## Authentication

v1 accepted an `api_key` query parameter. v2 requires a bearer token in the
`Authorization` header. Remove `api_key` from every URL.

## Pagination

v2 introduced `page` and `per_page` query parameters. The response includes a
`total_pages` field.

## Webhooks

v2 signs webhook payloads with an `X-Nimbus-Signature` header. Verify the
signature before processing a payload.

## Checklist

- [ ] Replace `api_key` with a bearer token
- [ ] Adopt page-based pagination
- [ ] Verify webhook signatures
