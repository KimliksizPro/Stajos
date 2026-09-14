# Fix-4 Infra/DB Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Align `log_topics.is_ai_suggested` model metadata with the existing head migration without generating a migration.

**Architecture:** Add one SQLAlchemy server-default declaration while preserving the Python default. Prove it with one metadata test, then validate Alembic only against a disposable SQLite database.

**Tech Stack:** Python, Flask, Flask-SQLAlchemy, SQLAlchemy, Flask-Migrate/Alembic, pytest, SQLite.

## Global Constraints

- Production OWNS: modify only `app/models/topic.py`.
- Test OWNS: create only `tests/test_fix4_infra_db.py`.
- Do not modify existing tests, `migrations/**`, `backlog.md`, `reports/**`, or any other file.
- Do not generate a migration. Head `migrations/versions/a2059b2bee86_faz3_learning.py:75` already has `server_default=sa.text('0')`.
- Keep `default=False`; add exactly `server_default=db.text("0")`.
- Optional CHECK constraints and the P1 stats bug are out of scope.
- Migration commands must target a fresh temporary SQLite file outside the workspace.
- Do not persistently modify `.env` or global/user environment variables.
- Downgrade only the disposable SQLite database.
- PostgreSQL verification is unavailable unless a dedicated disposable environment is supplied; never target production.
- This is not a Git repository; do not run Git or commit commands.

---

### Task 1: Metadata Contract (RED)

**Files:**
- Create: `tests/test_fix4_infra_db.py`
- Inspect: `app/models/topic.py:12-17`
- Inspect: `migrations/versions/a2059b2bee86_faz3_learning.py:72-79`

**Interfaces:**
- Consumes: `app.models.topic.log_topics` and SQLAlchemy column metadata.
- Produces: the nullability, Python-default, and server-default regression contract.

- [ ] **Step 1: Add the focused metadata test**

```python
from app.models.topic import log_topics


def test_log_topics_is_ai_suggested_defaults_match_head_migration():
    column = log_topics.c.is_ai_suggested

    assert column.nullable is False
    assert column.default is not None
    assert column.default.is_scalar
    assert column.default.arg is False
    assert column.server_default is not None
    assert str(column.server_default.arg).strip() == "0"
```

- [ ] **Step 2: Verify RED before production edits**

Run: `python -m pytest -v tests/test_fix4_infra_db.py`

Expected: one failure at `assert column.server_default is not None`. If the test errors earlier or passes, stop and reconcile it with the actual metadata before editing production code.

- [ ] **Step 3: Confirm existing migration evidence**

Run: `rg -n "is_ai_suggested.*server_default=sa\.text\('0'\)" migrations/versions/a2059b2bee86_faz3_learning.py`

Expected: one match at line 75. Do not create or modify a migration.

---

### Task 2: Minimal Metadata Alignment (GREEN)

**Files:**
- Modify: `app/models/topic.py:12-17`
- Test: `tests/test_fix4_infra_db.py`

**Interfaces:**
- Consumes: the existing `db` object and `log_topics` table.
- Produces: server-default SQL text `0` while retaining Python default `False`.

- [ ] **Step 1: Make the only production change**

Replace only the `is_ai_suggested` declaration with:

```python
db.Column(
    "is_ai_suggested",
    db.Boolean,
    nullable=False,
    default=False,
    server_default=db.text("0"),
),
```

Do not add a CHECK constraint, alter another column, or edit a migration.

- [ ] **Step 2: Verify focused GREEN**

Run: `python -m pytest -v tests/test_fix4_infra_db.py`

Expected: `1 passed`.

- [ ] **Step 3: Verify targeted regressions**

Run: `python -m pytest -v tests/test_fix1_data_quality.py tests/test_fix4_infra_db.py`

Expected: all selected tests pass, including the existing direct `log_topics` insert that omits `is_ai_suggested`.

---

### Task 3: Disposable SQLite Migration Lifecycle

**Files:**
- Verify only: `migrations/**`, `app/models/topic.py`
- Temporary artifact: `%TEMP%\stajos-fix4-migration.db`

**Interfaces:**
- Consumes: Flask CLI from `run.py`, `DATABASE_URL`, and the existing revision chain.
- Produces: isolated heads/history/upgrade/current/check/downgrade/upgrade evidence.

- [ ] **Step 1: Create a clean target and verify its URL**

Run: `if exist "%TEMP%\stajos-fix4-migration.db" del "%TEMP%\stajos-fix4-migration.db"`

Expected: exit code 0; no workspace file is deleted.

Run: `set "FLASK_ENV=development"&& set "DATABASE_URL=sqlite:///%TEMP:\=/%/stajos-fix4-migration.db"&& python -c "import os; print(os.environ['DATABASE_URL'])"`

Expected: output starts with `sqlite:///` and ends with `/stajos-fix4-migration.db`; it does not contain `stajos_dev.db`. The variables exist only in that command process.

- [ ] **Step 2: Inspect revision topology**

Run: `set "FLASK_ENV=development"&& set "DATABASE_URL=sqlite:///%TEMP:\=/%/stajos-fix4-migration.db"&& python -m flask --app run.py db heads`

Expected: one head, `a2059b2bee86`.

Run: `set "FLASK_ENV=development"&& set "DATABASE_URL=sqlite:///%TEMP:\=/%/stajos-fix4-migration.db"&& python -m flask --app run.py db history`

Expected: the linear chain includes `70a5135b18da`, `5678faa6d0c4`, and `a2059b2bee86 (head)`.

- [ ] **Step 3: Upgrade and inspect the disposable database**

Run: `set "FLASK_ENV=development"&& set "DATABASE_URL=sqlite:///%TEMP:\=/%/stajos-fix4-migration.db"&& python -m flask --app run.py db upgrade head`

Expected: exit code 0 and upgrades through `a2059b2bee86`.

Run: `set "FLASK_ENV=development"&& set "DATABASE_URL=sqlite:///%TEMP:\=/%/stajos-fix4-migration.db"&& python -m flask --app run.py db current`

Expected: `a2059b2bee86 (head)`.

Run: `set "FLASK_ENV=development"&& set "DATABASE_URL=sqlite:///%TEMP:\=/%/stajos-fix4-migration.db"&& python -m flask --app run.py db check`

Expected: exit code 0 and `No new upgrade operations detected.` No revision is generated.

- [ ] **Step 4: Downgrade only the disposable database and re-upgrade**

Run: `set "FLASK_ENV=development"&& set "DATABASE_URL=sqlite:///%TEMP:\=/%/stajos-fix4-migration.db"&& python -m flask --app run.py db downgrade 5678faa6d0c4`

Expected: exit code 0; only Faz 3 objects in the disposable file are removed.

Run: `set "FLASK_ENV=development"&& set "DATABASE_URL=sqlite:///%TEMP:\=/%/stajos-fix4-migration.db"&& python -m flask --app run.py db current`

Expected: `5678faa6d0c4`.

Run: `set "FLASK_ENV=development"&& set "DATABASE_URL=sqlite:///%TEMP:\=/%/stajos-fix4-migration.db"&& python -m flask --app run.py db upgrade head`

Expected: exit code 0 and upgrade to `a2059b2bee86`.

Run: `set "FLASK_ENV=development"&& set "DATABASE_URL=sqlite:///%TEMP:\=/%/stajos-fix4-migration.db"&& python -m flask --app run.py db current`

Expected: `a2059b2bee86 (head)`.

Run: `set "FLASK_ENV=development"&& set "DATABASE_URL=sqlite:///%TEMP:\=/%/stajos-fix4-migration.db"&& python -m flask --app run.py db check`

Expected: exit code 0 and `No new upgrade operations detected.`

- [ ] **Step 5: Remove the disposable database**

Run: `if exist "%TEMP%\stajos-fix4-migration.db" del "%TEMP%\stajos-fix4-migration.db"`

Expected: exit code 0. Do not delete or modify `stajos_dev.db`, `.env`, or any production database. Report PostgreSQL as unverified unless a separate disposable PostgreSQL environment was supplied.

---

### Task 4: Full Verification And Self-Review

**Files:**
- Verify: `app/models/topic.py`
- Verify: `tests/test_fix4_infra_db.py`
- Re-read: `docs/superpowers/specs/2026-09-14-fix4-infra-db-design.md`
- Re-read: `docs/superpowers/plans/2026-09-14-fix4-infra-db.md`

**Interfaces:**
- Consumes: completed Fix-4 implementation and migration evidence.
- Produces: test, compile, scope, and document-quality evidence; no commit.

- [ ] **Step 1: Run the full test suite**

Run: `python -m pytest -v`

Expected: all tests pass.

- [ ] **Step 2: Compile application and tests**

Run: `python -m py_compile app/models/topic.py tests/test_fix4_infra_db.py`

Expected: exit code 0 with no output.

Run: `python -m compileall -q app tests`

Expected: exit code 0 with no errors.

- [ ] **Step 3: Confirm exact scope and migration state**

Run: `rg -n "is_ai_suggested|server_default" app/models/topic.py migrations/versions/a2059b2bee86_faz3_learning.py tests/test_fix4_infra_db.py`

Expected: the model has `default=False` and `server_default=db.text("0")`; head has `server_default=sa.text('0')`; the test checks both defaults. Confirm no new file exists under `migrations/versions/`.

- [ ] **Step 4: Re-read and self-review**

Re-read both documents, `app/models/topic.py`, and `tests/test_fix4_infra_db.py`. Confirm there are no placeholders or contradictory commands; production scope is exactly one model edit; no migration or CHECK constraint was introduced; the P1 stats bug is untouched; every database lifecycle command uses the disposable `%TEMP%` SQLite URL; downgrade is limited to it; and PostgreSQL is reported unverified without a disposable PostgreSQL environment.

Run: `rg -n "TB[D]|TO[D]O|implement lat[e]r|fill in detail[s]" docs/superpowers/specs/2026-09-14-fix4-infra-db-design.md docs/superpowers/plans/2026-09-14-fix4-infra-db.md`

Expected: no matches. The split regex spellings prevent this command from matching itself.

- [ ] **Step 5: Report evidence**

Report under exactly `Decision | Files Changed | Evidence | Risks/Unknowns`, in at most 850 tokens. Include RED/GREEN, targeted/full pytest, compile, SQLite lifecycle results, unchanged migration inventory, no `.env`/global environment changes, and the PostgreSQL verification limitation.
