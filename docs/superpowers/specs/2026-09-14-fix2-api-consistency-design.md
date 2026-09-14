# Fix-2 API Consistency Design

## Decision

Fix-2 is a minimal consistency patch. Preserve the already-correct health route and stats bind lookup with regression tests. Change production code only in the timeline route, where `start_date` and `end_date` are parsed once for format validation and again for ordering.

## Scope

- Keep `app/__init__.py` health behavior and `app/services/stats_service.py` use of `db.session.get_bind()` unchanged.
- In `app/api/v1/timeline_routes.py`, parse each non-blank date argument exactly once into `s_date` / `e_date`.
- Reuse those objects for ordering and `TimelineService.get_timeline(start_date=..., end_date=...)`.
- Add endpoint regressions and narrow source/runtime introspection for the required structure.

## Non-Goals

- No service refactor, validation redesign, migration, dependency change, or unrelated cleanup.
- Do not move the 366-day rule from `TimelineService` into the route.
- Do not modify health, stats, backlog, reports, or existing Fix-1 tests.

## API Contract

All endpoints retain `{success, data, meta, errors}`.

- `GET /api/v1/health` and `/api/v1/health/` return 200 without redirect, with `success: true`, `data: {status: "ok"}`, `meta: null`, and `errors: []`.
- Authenticated `GET /api/v1/dashboard/stats` retains its status, envelope, and data keys. Stats continues to use `db.session.get_bind()`.
- Authenticated `GET /api/v1/timeline` retains current validation messages and statuses. A reversed range returns 400 with `errors: ["start_date end_date'den sonra olamaz"]`.
- An inclusive 366-day range succeeds. An inclusive 367-day range returns 400 with `errors: ["Tarih aralığı en fazla 366 gün olabilir"]`.
- Valid date strings become `datetime.date` values before service delegation. Missing/blank dates remain `None`; year/month behavior is unchanged.

## Test Design

Create `tests/test_fix2_api_consistency.py` using existing app/client fixtures.

- Call both real health URLs and assert the full envelope and no redirect.
- Call the real authenticated stats endpoint and assert its envelope/data shape. Inspect `StatsService._query_logs_per_month` to require `db.session.get_bind()` and reject `db.engine`.
- Call the real authenticated timeline endpoint for a valid range, reversed range, 366 days, and 367 days.
- Monkeypatch route-level `parse_date` and `TimelineService.get_timeline`; assert one parse per supplied date and that the service receives the same objects by identity. This fails before the production edit because the route parses twice and passes raw strings.

## Files And Verification

- Production: `app/api/v1/timeline_routes.py` only.
- Tests: new `tests/test_fix2_api_consistency.py` only.
- Verify with focused pytest, existing boundary tests, full pytest, `py_compile`, and `compileall`.
- The workspace is not a Git repository, so do not attempt a commit.
