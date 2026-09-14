import ast
import importlib.util
from pathlib import Path

import pytest


MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations" / "versions"


def _migration_source():
    matches = list(MIGRATIONS_DIR.glob("*_faz5_ai*.py"))
    assert len(matches) == 1
    return matches[0].read_text(encoding="utf-8")


def _load_migration():
    path = next(MIGRATIONS_DIR.glob("*_faz5_ai*.py"))
    spec = importlib.util.spec_from_file_location("faz5_ai_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Result:
    def __init__(self, row):
        self.row = row

    def first(self):
        return self.row


class _Bind:
    def __init__(self, processing_row=None):
        self.dialect = type("Dialect", (), {"name": "postgresql"})()
        self.processing_row = processing_row
        self.events = []

    def execute(self, statement):
        self.events.append(("query", str(statement)))
        return _Result(self.processing_row)

    def begin(self):
        bind = self

        class Transaction:
            def __enter__(self):
                bind.events.append(("transaction", "begin"))

            def __exit__(self, exc_type, exc_value, traceback):
                bind.events.append(
                    ("transaction", "rollback" if exc_type else "commit")
                )

        return Transaction()


class _Batch:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def drop_column(self, name):
        pass


class _Op:
    def __init__(self, bind, fail_on=None):
        self.bind = bind
        self.fail_on = fail_on

    def get_bind(self):
        return self.bind

    def execute(self, statement):
        sql = str(statement)
        self.bind.events.append(("ddl", sql))
        if self.fail_on and self.fail_on in sql:
            raise RuntimeError("simulated DDL failure")

    def batch_alter_table(self, table_name, schema=None):
        return _Batch()


def test_faz5_migration_links_to_existing_head_and_adds_required_columns():
    source = _migration_source()
    tree = ast.parse(source)
    assignments = {
        node.targets[0].id: ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id in {"revision", "down_revision"}
    }

    assert assignments["revision"] != assignments["down_revision"]
    assert assignments["down_revision"] == "a2059b2bee86"
    for column in (
        "ai_suggested_technologies",
        "ai_suggested_topics",
        "ai_suggested_tags",
        "ai_processing_started_at",
    ):
        assert f'"{column}"' in source
    assert source.count("sa.JSON()") == 3
    assert "sa.DateTime(timezone=True)" in source


def test_faz5_migration_handles_postgresql_enum_explicitly_and_portably():
    source = _migration_source()
    tree = ast.parse(source)
    altered_columns = [
        ast.literal_eval(node.args[0])
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "alter_column"
        and node.args
    ]

    assert 'dialect.name == "postgresql"' in source
    assert "ALTER TYPE ai_status ADD VALUE IF NOT EXISTS 'PROCESSING'" in source
    assert "PROCESSING rows must be resolved before downgrade" in source
    assert 'dialect.name == "sqlite"' in source
    assert altered_columns.count("ai_status") == 2
    assert "op.batch_alter_table" in source


def test_postgresql_downgrade_guard_runs_before_any_mutation(monkeypatch):
    migration = _load_migration()
    bind = _Bind(processing_row=(1,))
    monkeypatch.setattr(migration, "op", _Op(bind))

    with pytest.raises(
        RuntimeError, match="PROCESSING rows must be resolved before downgrade"
    ):
        migration.downgrade()

    assert bind.events == [
        (
            "query",
            "SELECT 1 FROM daily_logs WHERE ai_status = 'PROCESSING' LIMIT 1",
        )
    ]


def test_postgresql_downgrade_recreates_enum_atomically_in_order(monkeypatch):
    migration = _load_migration()
    bind = _Bind()
    monkeypatch.setattr(migration, "op", _Op(bind))

    migration.downgrade()

    assert bind.events == [
        (
            "query",
            "SELECT 1 FROM daily_logs WHERE ai_status = 'PROCESSING' LIMIT 1",
        ),
        ("transaction", "begin"),
        ("ddl", "ALTER TYPE ai_status RENAME TO ai_status_with_processing"),
        (
            "ddl",
            "CREATE TYPE ai_status AS ENUM "
            "('PENDING', 'REFINED', 'ACCEPTED', 'REJECTED', 'ERROR')",
        ),
        (
            "ddl",
            "ALTER TABLE daily_logs ALTER COLUMN ai_status TYPE ai_status "
            "USING ai_status::text::ai_status",
        ),
        ("ddl", "DROP TYPE ai_status_with_processing"),
        ("transaction", "commit"),
    ]


def test_postgresql_downgrade_rolls_back_enum_recreation_on_failure(monkeypatch):
    migration = _load_migration()
    bind = _Bind()
    monkeypatch.setattr(
        migration,
        "op",
        _Op(bind, fail_on="ALTER TABLE daily_logs ALTER COLUMN ai_status"),
    )

    with pytest.raises(RuntimeError, match="simulated DDL failure"):
        migration.downgrade()

    assert bind.events[-1] == ("transaction", "rollback")
    assert ("ddl", "DROP TYPE ai_status_with_processing") not in bind.events
