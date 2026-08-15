---
name: dynamodb-query-first-api
description: Design and review DynamoDB-backed HTTP APIs around access patterns, GSIs, cursor pagination, database-side filtering and sorting, schema migration, and safe storage error handling. Use for FastAPI or other services that list, search, filter, sort, paginate, or migrate DynamoDB data; especially when code uses Scan, loads full tables, implements offset pagination, or leaks SDK errors.
---

# DynamoDB Query-First API

Design the table from API access patterns before implementing handlers.

## Workflow

1. List every read pattern, including partition scope, filters, sort field, direction, and page size.
2. Reject request-path full-table `Scan` and in-memory sort/filter/pagination. Use `Query` with a table key or GSI.
3. Add stable index keys to writes. Backfill old items once during a migration, never on each request.
4. Use `LastEvaluatedKey` as an opaque encoded cursor. Do not offer offset pages, exact totals, or page counts unless a separate maintained counter justifies their cost.
5. Set `Limit`, `ScanIndexForward`, `KeyConditionExpression`, and—only when the key cannot express it—`FilterExpression` in DynamoDB.
6. Remember that `FilterExpression` runs after reads. For selective/high-volume filters, create a composite partition key or dedicated GSI instead.
7. Test the exact SDK query arguments plus cursor round-tripping. Then run against DynamoDB Local with existing data.
8. Map validation and cursor errors to `4xx`, retryable storage failures to `503`, and unexpected storage failures to a non-leaking `500`. Log the original exception.

## Release gate

- Verify no request-path function calls `Scan` for collection reads.
- Verify every supported sort uses an index sort key.
- Verify newly written and migrated items contain every index attribute.
- Restart the app and confirm cursor pagination and persistence still work.
