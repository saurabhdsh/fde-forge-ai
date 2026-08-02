"""Python playground syntax checker tests."""

from app.services.python_syntax import check_python_syntax


def test_valid_python_has_no_errors() -> None:
    diags = check_python_syntax("def add(a, b):\n    return a + b\n")
    assert not any(d.severity == "error" for d in diags)


def test_syntax_error_reported_with_line() -> None:
    diags = check_python_syntax("def broken(\n    return 1\n")
    assert diags
    assert any("python" in d.source for d in diags)


def test_unmatched_paren_warning() -> None:
    diags = check_python_syntax("print('hi'\n")
    assert diags


def test_indent_error_is_hard_error() -> None:
    diags = check_python_syntax("def f():\nreturn 1\n")
    assert any(d.severity == "error" for d in diags)
    assert any(d.line == 2 for d in diags)
