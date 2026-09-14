# Fix-3 Structure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply Fix-3 structural cleanup while preserving API and fallback behavior.

**Architecture:** Keep serialization on models and reuse `iso_or_none` only for nullable values. Eager-loading remains optional: warn on setup failure, then execute the unchanged base query.

**Tech Stack:** Python, Flask, Flask-SQLAlchemy, SQLAlchemy, pytest.

## Global Constraints

- Production OWNS: `app/core/pagination.py`, `app/models/internship.py`, `app/models/user.py`, `app/api/v1/auth_routes.py`, `app/services/auth_service.py`, `app/services/internship_service.py`, `app/services/log_service.py`, `app/services/stats_service.py`, `app/services/timeline_service.py`.
- Test OWNS: create `tests/test_fix3_structure.py` only.
- Do not modify any other file.
- Preserve auth fields exactly; never serialize `password_hash`.
- Reuse `app.utils.time.iso_or_none`; create no helper/module.
- Keep direct `.isoformat()` for mandatory/non-null timeline dates.
- Swallow the three eager-load exceptions after contextual WARNING records.
- P1 stats empty-user behavior is out of scope.
- This is not a Git repository; do not run Git or commit commands.

---

### Task 1: Contract Tests (RED)

**OWNS:**
- Create: `tests/test_fix3_structure.py`

**Interfaces:**
- Consumes: existing `app`/`client` fixtures, models, services, and pagination.
- Produces: serialization, auth, import, timeline, and logging contracts.

- [ ] **Step 1: Add serialization and auth tests**

```python
def test_user_to_dict_exact_and_safe():
    user = User(id="u1", email="a@b.com", full_name="A", password_hash="secret",
                created_at=datetime(2026, 9, 14, tzinfo=timezone.utc))
    assert user.to_dict() == {"id": "u1", "email": "a@b.com", "full_name": "A",
                              "created_at": "2026-09-14T00:00:00+00:00"}
    assert "password_hash" not in user.to_dict()
    user.created_at = None
    assert user.to_dict()["created_at"] is None
```

Also exercise register, login, and `/me` using `client`. Assert exact data key sets `{id,email,full_name}`, `{user,access_token,refresh_token}` with nested `{id,email,full_name}`, and `{id,email,full_name,created_at}` respectively. Recursively assert `password_hash` is absent from all three response bodies.

- [ ] **Step 2: Add nullable and structure tests**

Create a persisted user and active internship. Assert `Internship.to_dict()` and `StatsService.get_dashboard_stats(user.id)["active_internship"]` retain their existing ISO values and fields. Add AST assertions for:

```python
assert pagination.__all__ == ["get_pagination_params", "paginate_query"]
for path in ("app/models/internship.py", "app/models/user.py", "app/services/stats_service.py"):
    assert "iso_or_none" in imported_names(path)
for path, forbidden in {
    "app/services/internship_service.py": {"datetime"},
    "app/services/log_service.py": {"date", "time", "TopicModel"},
    "app/services/stats_service.py": {"timedelta"},
    "app/services/timeline_service.py": {"db"},
}.items():
    assert imported_names(path).isdisjoint(forbidden)
```

Read `timeline_service.py` and assert it still contains `cur.isoformat()`, `d.isoformat()`, `range_start.isoformat()`, and `range_end.isoformat()`.

- [ ] **Step 3: Add runtime logging tests**

For each service module, monkeypatch `selectinload` to raise `RuntimeError("loader unavailable")`. With a persisted user/internship and no logs, call `StatsService._query_recent_logs`, `TimelineService.get_timeline`, and `LogService.get_logs`. Assert they return `[]`, `([], {"total_logs": 0, "total_days": 0})`, and `([], 0)` and capture exactly one WARNING each:

```text
Failed to configure eager loading for recent logs: loader unavailable
Failed to configure eager loading for timeline logs: loader unavailable
Failed to configure eager loading for log list: loader unavailable
```

- [ ] **Step 4: Verify RED**

Run: `python -m pytest -v tests/test_fix3_structure.py`

Expected: FAIL for missing `User.to_dict`, pagination `__all__`, helper imports, unused imports, and silent eager-load handlers. Existing response value assertions may pass as regression locks.

---

### Task 2: Serialization And Imports (GREEN)

**OWNS:**
- Modify: `app/core/pagination.py`
- Modify: `app/models/internship.py`
- Modify: `app/models/user.py`
- Modify: `app/api/v1/auth_routes.py`
- Modify: `app/services/auth_service.py`
- Modify: `app/services/internship_service.py`
- Modify: `app/services/log_service.py`
- Modify: `app/services/stats_service.py`
- Modify: `app/services/timeline_service.py`
- Test: `tests/test_fix3_structure.py`

**Interfaces:**
- Consumes: `iso_or_none(value) -> Optional[str]`.
- Produces: `User.to_dict() -> dict` and pagination exports.

- [ ] **Step 1: Add exports and serializers**

```python
# pagination.py
__all__ = ["get_pagination_params", "paginate_query"]

# user.py
def to_dict(self) -> dict:
    return {
        "id": self.id,
        "email": self.email,
        "full_name": self.full_name,
        "created_at": iso_or_none(self.created_at),
    }
```

Import `iso_or_none` beside `_utcnow` in `user.py` and `internship.py`. In `Internship.to_dict()`, replace the four nullable date/timestamp ternaries with `iso_or_none`. In stats, import it and replace only active internship `start_date` and `end_date` ternaries.

- [ ] **Step 2: Delegate auth with exact field selection**

```python
user_data = user.to_dict()
public_user = {key: user_data[key] for key in ("id", "email", "full_name")}
```

Use `public_user` for register and login; retain both token fields. Use full `user.to_dict()` for `/me`. Do not expose `created_at` on register/login or `password_hash` anywhere.

- [ ] **Step 3: Remove only verified imports**

Remove `datetime` from internship service; `date`, `time`, and `TopicModel` from log service; `timedelta` from stats; and `db` from timeline. Change the stale log-service sentence to `Uses Topic.normalized_name semantics, not lower(name).` Remove nothing else.

- [ ] **Step 4: Verify focused GREEN**

Run: `python -m pytest -v tests/test_fix3_structure.py -k "not eager_load"`

Expected: all selected tests pass.

---

### Task 3: Eager-Load Warnings (GREEN)

**OWNS:**
- Modify: `app/services/log_service.py`
- Modify: `app/services/stats_service.py`
- Modify: `app/services/timeline_service.py`
- Test: `tests/test_fix3_structure.py`

**Interfaces:**
- Consumes: standard `logging` and existing fallback blocks.
- Produces: one warning per caught eager-load setup failure.

- [ ] **Step 1: Add missing module loggers**

```python
import logging

logger = logging.getLogger(__name__)
```

Add this to stats and timeline; keep log service's existing logger.

- [ ] **Step 2: Replace only three silent catches**

```python
except Exception as error:
    logger.warning("Failed to configure eager loading for recent logs: %s", error)
```

Use the exact corresponding `timeline logs` and `log list` messages in those services. Do not re-raise, return early, alter the query, or change any other exception handler.

- [ ] **Step 3: Verify Fix-3 GREEN**

Run: `python -m pytest -v tests/test_fix3_structure.py`

Expected: all Fix-3 tests pass.

---

### Task 4: Verification And Self-Review

**OWNS:**
- Verify only: every file in Global Constraints.

**Interfaces:**
- Consumes: completed implementation.
- Produces: test, compile/import, and scope evidence; no commit.

- [ ] **Step 1: Run targeted and full tests**

Run: `python -m pytest -v tests/test_auth.py tests/test_fix2_api_contract.py tests/test_fix3_structure.py`

Expected: all selected tests pass.

Run: `python -m pytest -v`

Expected: all tests pass.

- [ ] **Step 2: Run compile/import smoke**

Run: `python -m py_compile app/core/pagination.py app/models/internship.py app/models/user.py app/api/v1/auth_routes.py app/services/auth_service.py app/services/internship_service.py app/services/log_service.py app/services/stats_service.py app/services/timeline_service.py tests/test_fix3_structure.py`

Expected: exit code 0, no output.

Run: `python -m compileall -q app tests`

Expected: exit code 0, no errors.

Run: `python -c "from app.core.pagination import get_pagination_params, paginate_query; from app.models.user import User; from app.services.log_service import LogService; from app.services.stats_service import StatsService; from app.services.timeline_service import TimelineService; print('import-ok')"`

Expected: `import-ok`.

- [ ] **Step 3: Re-read and self-review**

Re-read every owned file. Search the two documents and changed code for `TBD|TODO|implement later`. Confirm exact auth keys, no `password_hash`, only nullable helper conversions, unchanged mandatory timeline `.isoformat()` calls, exactly three contextual warnings, unchanged fallback continuation, no P1 empty-user fix, and no edits outside OWNS.

Run: `rg -n "TBD|TODO|implement later|password_hash|iso_or_none|Failed to configure eager loading" docs/superpowers/specs/2026-09-14-fix3-structure-design.md docs/superpowers/plans/2026-09-14-fix3-structure.md app tests/test_fix3_structure.py`

Expected: no placeholder hits; `password_hash` only in model/auth security and explicit exclusion tests; helper and warning hits match this plan.
