import ast
from pathlib import Path

from app.models.topic import log_topics


def test_log_topics_is_ai_suggested_defaults_match_head_migration():
    column = log_topics.c.is_ai_suggested

    assert column.nullable is False
    assert column.default is not None
    assert column.default.is_scalar
    assert column.default.arg is False
    assert column.server_default is not None
    assert str(column.server_default.arg).strip() == "0"

    migration_path = (
        Path(__file__).parents[1]
        / "migrations"
        / "versions"
        / "a2059b2bee86_faz3_learning.py"
    )
    tree = ast.parse(migration_path.read_text(encoding="utf-8"))
    migration_column = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "Column"
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and node.args[0].value == "is_ai_suggested"
    )
    server_default = next(
        keyword.value
        for keyword in migration_column.keywords
        if keyword.arg == "server_default"
    )

    assert isinstance(server_default, ast.Call)
    assert isinstance(server_default.func, ast.Attribute)
    assert server_default.func.attr == "text"
    assert server_default.args[0].value == "0"
