"""Task 5 fix: startup recovery contract (source-level, no run.py import).

run.py is the real startup path; importing it would call create_app() as a
side effect, so these tests inspect its source (same practice as
test_migration.py) plus exec only the guarded try/except snippet with fakes.
"""

import ast
from pathlib import Path

RUN_PY = Path(__file__).resolve().parents[2] / "run.py"
APP_INIT = Path(__file__).resolve().parents[2] / "app" / "__init__.py"


def _source():
    return RUN_PY.read_text(encoding="utf-8")


def _tree():
    return ast.parse(_source())


def _recovery_try_node():
    for node in ast.walk(_tree()):
        if isinstance(node, ast.Try):
            for sub in ast.walk(node):
                if (
                    isinstance(sub, ast.Call)
                    and isinstance(sub.func, ast.Name)
                    and sub.func.id == "start_ai_recovery"
                ):
                    return node
    raise AssertionError("run.py has no try-guarded start_ai_recovery(app) call")


def test_run_imports_recovery_hook():
    tree = _tree()
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "app.ai.factory":
            imported.update(a.asname or a.name for a in node.names)
    assert "start_ai_recovery" in imported
    assert "create_app" in _source()


def test_run_calls_recovery_after_create_app_guarded_by_warning():
    tree = _tree()
    create_lineno = next(
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "app" for t in node.targets)
        and isinstance(node.value, ast.Call)
        and getattr(node.value.func, "id", "") == "create_app"
    )
    try_node = _recovery_try_node()
    assert try_node.lineno > create_lineno

    call = next(
        sub
        for sub in ast.walk(try_node)
        if isinstance(sub, ast.Call)
        and isinstance(sub.func, ast.Name)
        and sub.func.id == "start_ai_recovery"
    )
    assert len(call.args) == 1
    assert isinstance(call.args[0], ast.Name) and call.args[0].id == "app"

    assert try_node.handlers, "recovery call must be inside try/except"
    catches_exception = any(
        h.type is None
        or (isinstance(h.type, ast.Name) and h.type.id in {"Exception", "BaseException"})
        or (
            isinstance(h.type, ast.Tuple)
            and any(
                isinstance(e, ast.Name) and e.id == "Exception" for e in h.type.elts
            )
        )
        for h in try_node.handlers
    )
    assert catches_exception

    warning_calls = [
        sub
        for h in try_node.handlers
        for sub in ast.walk(h)
        if isinstance(sub, ast.Call)
        and isinstance(sub.func, ast.Attribute)
        and sub.func.attr == "warning"
        and isinstance(sub.func.value, ast.Name)
        and sub.func.value.id == "logger"
    ]
    assert warning_calls, "except handler must logger.warning (no process kill)"
    assert "sys.exit" not in _source() and "raise" not in ast.get_source_segment(
        _source(), try_node.handlers[0]
    )


def _exec_recovery_guard(fake_recovery):
    try_node = _recovery_try_node()
    segment = ast.get_source_segment(_source(), try_node)
    assert segment is not None

    class FakeLogger:
        def __init__(self):
            self.warnings = []

        def warning(self, *args, **kwargs):
            self.warnings.append((args, kwargs))

    fake_logger = FakeLogger()
    namespace = {
        "start_ai_recovery": fake_recovery,
        "app": object(),
        "logger": fake_logger,
    }
    exec(compile(segment, str(RUN_PY), "exec"), namespace)  # noqa: S102 - test-only exec of local snippet
    return fake_logger


def test_run_recovery_guard_warns_and_continues_on_exception():
    def boom(app_arg):
        raise RuntimeError("db down")

    fake_logger = _exec_recovery_guard(boom)

    assert len(fake_logger.warnings) == 1  # no exception propagated


def test_run_recovery_guard_stays_quiet_on_success():
    seen = []

    def ok(app_arg):
        seen.append(app_arg)
        return 3

    fake_logger = _exec_recovery_guard(ok)

    assert len(seen) == 1
    assert fake_logger.warnings == []


def test_run_preserves_main_block():
    source = _source()
    main = next(
        node
        for node in ast.walk(_tree())
        if isinstance(node, ast.If)
        and isinstance(node.test, ast.Compare)
        and isinstance(node.test.left, ast.Name)
        and node.test.left.id == "__name__"
    )
    segment = ast.get_source_segment(source, main)
    assert segment is not None
    assert "app.run(" in segment
    assert (
        'app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), '
        'debug=app.config.get("DEBUG", False))' in segment
    )


def test_create_app_still_never_runs_recovery():
    tree = ast.parse(APP_INIT.read_text(encoding="utf-8"))
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and (
            (isinstance(node.func, ast.Name) and node.func.id == "start_ai_recovery")
            or (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "start_ai_recovery"
            )
        )
    ]
    assert calls == []
