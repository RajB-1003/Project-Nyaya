"""
strip_comments.py -- Remove all comments from Project Nyaya source files.
- Python files: uses tokenize (safe, won't touch strings)
- TS/TSX/JS files: regex-based (handles // and block comments)
"""
import io
import re
import tokenize
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent  # d:\project-nyaya

PY_FILES = [
    ROOT / "backend" / "main.py",
    ROOT / "backend" / "form_pdf_builder.py",
    ROOT / "backend" / "web_fetcher.py",
    ROOT / "backend" / "test_web_fetch.py",
    ROOT / "backend" / "patch_prompt.py",
]

TS_FILES = [
    ROOT / "frontend" / "src" / "app" / "page.tsx",
    ROOT / "frontend" / "src" / "app" / "layout.tsx",
    ROOT / "frontend" / "src" / "components" / "MicButton.tsx",
    ROOT / "frontend" / "src" / "components" / "ResultCard.tsx",
    ROOT / "frontend" / "src" / "components" / "FormCollector.tsx",
    ROOT / "frontend" / "src" / "components" / "DownloadButton.tsx",
    ROOT / "frontend" / "src" / "components" / "Timeline.tsx",
    ROOT / "frontend" / "src" / "data" / "timelines.js",
]


# ── Python comment stripper (tokenize-based) ──────────────────────────────────
def strip_python_comments(source: str) -> str:
    result = []
    prev_toktype = tokenize.ENCODING
    last_lineno = -1
    last_col = 0

    tokens = tokenize.generate_tokens(io.StringIO(source).readline)
    for tok_type, tok_string, tok_start, tok_end, _ in tokens:
        if tok_type == tokenize.COMMENT:
            continue  # drop the comment token
        if tok_type == tokenize.STRING:
            # Keep all string literals (including docstrings)
            pass
        if tok_type == tokenize.NEWLINE or tok_type == tokenize.NL:
            if prev_toktype == tokenize.COMMENT:
                tok_string = "\n"
        start_line, start_col = tok_start
        if start_line > last_lineno:
            result.append("\n" * (start_line - last_lineno - 1))
            last_col = 0
        if start_col > last_col:
            result.append(" " * (start_col - last_col))
        result.append(tok_string)
        last_lineno, last_col = tok_end
        prev_toktype = tok_type

    return "".join(result)


# ── TypeScript/JS comment stripper (regex-based) ─────────────────────────────
def strip_ts_comments(source: str) -> str:
    # Remove block comments /* ... */ (non-greedy, dotall)
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    # Remove line comments // ... but NOT inside strings.
    # Strategy: match strings first, then // comments.
    # Simple approach: only strip // when not inside a string literal by
    # removing // to end-of-line, but protect http:// style URLs.
    def remove_line_comment(line: str) -> str:
        # Walk the line char by char, tracking string state
        in_single = False
        in_double = False
        i = 0
        while i < len(line):
            c = line[i]
            if c == "'" and not in_double:
                in_single = not in_single
            elif c == '"' and not in_single:
                in_double = not in_double
            elif c == "/" and not in_single and not in_double:
                if i + 1 < len(line) and line[i + 1] == "/":
                    # Check it's not http:// or similar (preceded by :)
                    if i > 0 and line[i - 1] == ":":
                        pass  # URL -- keep
                    else:
                        return line[:i].rstrip()
            i += 1
        return line

    lines = source.splitlines()
    cleaned = [remove_line_comment(l) for l in lines]
    # Collapse 3+ consecutive blank lines into 2
    result = []
    blank_run = 0
    for line in cleaned:
        if line.strip() == "":
            blank_run += 1
            if blank_run <= 2:
                result.append(line)
        else:
            blank_run = 0
            result.append(line)
    return "\n".join(result)


# ── Run ───────────────────────────────────────────────────────────────────────
total = 0
for path in PY_FILES:
    if not path.exists():
        print(f"  SKIP (not found): {path.name}")
        continue
    src = path.read_text(encoding="utf-8")
    try:
        stripped = strip_python_comments(src)
    except tokenize.TokenError as e:
        print(f"  ERROR tokenizing {path.name}: {e}")
        continue
    path.write_text(stripped, encoding="utf-8")
    before = src.count("\n")
    after = stripped.count("\n")
    print(f"  PY  {path.name}: {before - after} comment lines removed")
    total += 1

for path in TS_FILES:
    if not path.exists():
        print(f"  SKIP (not found): {path.name}")
        continue
    src = path.read_text(encoding="utf-8")
    stripped = strip_ts_comments(src)
    path.write_text(stripped, encoding="utf-8")
    before = src.count("\n")
    after = stripped.count("\n")
    print(f"  TS  {path.name}: {before - after} comment lines removed")
    total += 1

print(f"\nDone -- {total} files processed.")
