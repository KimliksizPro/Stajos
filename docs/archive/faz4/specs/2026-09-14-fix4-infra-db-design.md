# Fix-4 Infra/DB Design

## Decision

Fix the `log_topics.is_ai_suggested` metadata drift by changing only its declaration in `app/models/topic.py`:

```python
db.Column(
    "is_ai_suggested",
    db.Boolean,
    nullable=False,
    default=False,
    server_default=db.text("0"),
)
```

This is a metadata correction, not a schema change. The current head migration, `migrations/versions/a2059b2bee86_faz3_learning.py:75`, already creates the column with `server_default=sa.text('0')`. No migration will be created or edited.

## Scope

- Production change: only `app/models/topic.py`.
- Implementation test: create only `tests/test_fix4_infra_db.py`.
- Preserve `default=False` as the Python-side default.
- Add exactly `server_default=db.text("0")` to align model metadata with the existing database migration.
- Do not change other models, services, routes, configuration, dependencies, or migrations.
- Optional CHECK constraints and the P1 stats bug are out of scope.
- The workspace is not a Git repository; do not run Git or commit commands.

## Test Design

The test inspects the real `log_topics` SQLAlchemy metadata. It asserts that `is_ai_suggested` is non-nullable, retains scalar Python default `False`, and has server-default SQL text `0`. The RED run must fail specifically because `server_default` is absent before the model edit.

After GREEN, run the focused test, relevant existing data-quality tests, the full suite, and Python compilation.

## Migration Validation

Use a fresh SQLite file outside the workspace, such as `%TEMP%\stajos-fix4-migration.db`. Every Flask command gets process-local `FLASK_ENV=development` and `DATABASE_URL=sqlite:///...` overrides. Do not edit `.env`, shell profiles, configuration, or global/user environment variables.

Run `flask db heads`, `history`, `upgrade`, `current`, and `check`. Then downgrade only the disposable database from `a2059b2bee86` to `5678faa6d0c4`, upgrade it to `head` again, and repeat `current` and `check`. Never downgrade the workspace or production database. Delete the disposable file afterward.

Production PostgreSQL behavior cannot be verified unless a dedicated disposable PostgreSQL environment and credentials are supplied. SQLite migration success is compatibility evidence, not a substitute for PostgreSQL validation.

## Self-Review

Re-read this spec, the implementation plan, the new test, and `app/models/topic.py`. Check for placeholders, contradictions, accidental scope expansion, migration edits, CHECK constraints, P1 stats changes, unsafe database targets, and any claim of PostgreSQL verification without evidence.

## Risks And Unknowns

- SQLAlchemy renders Boolean defaults differently by dialect; the metadata test validates the configured SQL expression `0`, not PostgreSQL execution semantics.
- `flask db check` against SQLite does not prove dialect-specific PostgreSQL behavior.
- Production PostgreSQL remains unverified when no disposable PostgreSQL environment is available.
