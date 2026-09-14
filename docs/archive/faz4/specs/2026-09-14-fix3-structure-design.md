# Fix-3 Structure Design

## Decision

Fix-3 is a behavior-preserving structural cleanup. Remove only imports verified unused in the current source, declare the pagination public API, reuse the existing `app.utils.time.iso_or_none` helper at equivalent nullable serialization sites, centralize safe user serialization in `User.to_dict()`, and replace three silent eager-load fallbacks with contextual warnings while continuing without eager loading.

## Scope

- Remove `datetime` from `app/services/internship_service.py`.
- Remove `date`, `time`, and `Topic as TopicModel` from `app/services/log_service.py`; update its stale `TopicModel` docstring reference.
- Remove `timedelta` from `app/services/stats_service.py` and `db` from `app/services/timeline_service.py`.
- Add `__all__ = ["get_pagination_params", "paginate_query"]` to `app/core/pagination.py` without changing either function.
- Use existing `iso_or_none` for nullable `Internship.to_dict()` dates/timestamps and nullable active-internship dates in stats.
- Add `User.to_dict() -> dict` returning exactly `id`, `email`, `full_name`, and `created_at`; never include `password_hash`.
- Reuse `User.to_dict()` in auth register, login, and `/me`, selecting keys where needed so every endpoint keeps its current fields.
- Add module loggers and warnings to the eager-load fallbacks in stats, timeline, and log services.

## Behavior Contracts

- Register data remains `{id, email, full_name}`.
- Login data remains `{user, access_token, refresh_token}` and nested `user` remains `{id, email, full_name}`.
- `/me` data remains `{id, email, full_name, created_at}`.
- `password_hash` is absent from `User.to_dict()` and every auth response under all circumstances.
- Internship and stats output keys and values remain unchanged.
- Timeline calendar and metadata dates are mandatory/non-null at their call sites. Keep their direct `.isoformat()` calls; do not blindly route them through a nullable helper.
- Each eager-load exception remains swallowed and the base query still executes. Emit one WARNING containing context and exception text:
  - `Failed to configure eager loading for recent logs: %s`
  - `Failed to configure eager loading for timeline logs: %s`
  - `Failed to configure eager loading for log list: %s`
- Do not add a serialization helper or module.

## Test Design

Create `tests/test_fix3_structure.py` before production changes.

- Test `User.to_dict()` for its exact safe key set, nullable ISO behavior, and exclusion of `password_hash`.
- Exercise register, login, and `/me`; assert exact existing fields and recursively reject `password_hash`.
- Test internship and stats serialization with real values.
- Assert pagination `__all__`; use narrow AST checks for the explicit unused-import list, helper imports, and continued direct timeline serialization.
- Force each eager-load `query.options(...)` call to raise; assert the method still returns through the base query and logs one contextual WARNING with exception text.

## Non-Goals

- Do not fix or test the P1 stats empty-user bug.
- Do not change API envelopes, statuses, validation, query semantics, pagination behavior, schema, dependencies, or migrations.
- Do not convert mandatory/non-null timeline serialization to `iso_or_none`.
- Do not alter other exception handlers or remove imports beyond the explicit list.
- Do not modify existing tests, backlog, reports, or files outside the implementation ownership below.

## Owned Implementation Files

- `app/core/pagination.py`
- `app/models/internship.py`
- `app/models/user.py`
- `app/api/v1/auth_routes.py`
- `app/services/auth_service.py`
- `app/services/internship_service.py`
- `app/services/log_service.py`
- `app/services/stats_service.py`
- `app/services/timeline_service.py`
- `tests/test_fix3_structure.py`

## Verification

- Record expected RED failures from the new tests before production edits.
- Run focused Fix-3 tests, existing auth/Fix-2 regressions, the full suite, direct `py_compile`, `compileall`, and import smoke.
- Re-read changed files and check exact auth fields, no `password_hash`, three contextual warnings, direct mandatory timeline serialization, and no P1 stats change.
- The workspace is not a Git repository; do not run Git or commit commands.
