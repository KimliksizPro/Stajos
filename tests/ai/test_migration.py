import ast
from pathlib import Path


MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations" / "versions"


def _migration_source():
    matches = list(MIGRATIONS_DIR.glob("*_faz5_ai*.py"))
    assert len(matches) == 1
    return matches[0].read_text(encoding="utf-8")


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
