"""Safe Python syntax checking (compile only — never executes user code)."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class Diagnostic:
    line: int
    column: int
    message: str
    severity: str = "error"
    source: str = "python"


def check_python_syntax(code: str) -> list[Diagnostic]:
    """Return compiler-style diagnostics for Python source."""
    text = code if code is not None else ""
    diagnostics: list[Diagnostic] = []

    # Fast structural hints (complaints while still typing)
    opens = {"(": ")", "[": "]", "{": "}"}
    closes = {")", "]", "}"}
    stack: list[tuple[str, int, int]] = []
    in_str: str | None = None
    escape = False
    lines = text.splitlines() or [""]
    for li, line in enumerate(lines, start=1):
        i = 0
        while i < len(line):
            ch = line[i]
            if in_str:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == in_str:
                    in_str = None
                i += 1
                continue
            if ch in ("'", '"'):
                # Heuristic for triple quotes
                if line[i : i + 3] in ("'''", '"""'):
                    in_str = line[i : i + 3]
                    i += 3
                    continue
                in_str = ch
                i += 1
                continue
            if ch == "#":
                break
            if ch in opens:
                stack.append((ch, li, i + 1))
            elif ch in closes:
                if not stack or opens.get(stack[-1][0]) != ch:
                    diagnostics.append(
                        Diagnostic(
                            line=li,
                            column=i + 1,
                            message=f"Unmatched '{ch}'",
                            severity="warning",
                            source="structure",
                        )
                    )
                else:
                    stack.pop()
            i += 1

    # Official compiler — no execution
    try:
        compile(text, "<playground>", "exec")
    except SyntaxError as exc:
        msg = exc.msg or "SyntaxError"
        line = int(exc.lineno or 1)
        col = int(exc.offset or 1)
        # Soften incomplete-input noise while typing (EOF mid-structure)
        soft = any(
            s in msg.lower()
            for s in (
                "unexpected eof",
                "was never closed",
                "eof while scanning",
            )
        )
        diagnostics.append(
            Diagnostic(
                line=max(1, line),
                column=max(1, col),
                message=msg,
                severity="warning" if soft else "error",
                source="python",
            )
        )
    except ValueError as exc:
        # e.g. null bytes
        diagnostics.append(
            Diagnostic(line=1, column=1, message=str(exc), severity="error", source="python")
        )

    # Deduplicate near-identical messages on same line
    seen: set[tuple[int, str]] = set()
    unique: list[Diagnostic] = []
    for d in diagnostics:
        key = (d.line, d.message)
        if key in seen:
            continue
        seen.add(key)
        unique.append(d)
    return unique[:20]


def looks_like_python(code: str) -> bool:
    return bool(re.search(r"[a-zA-Z_]|\n|:|\(|\[", code or ""))
