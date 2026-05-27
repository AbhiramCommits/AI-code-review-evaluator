import ast
import json
import os
import re
import sys
from pathlib import Path

APP_DIR = Path(__file__).parent / "app"
ROUTES_DIR = APP_DIR / "routes"
MODELS_DIR = APP_DIR / "models"


def _collect_py_files(directory):
    return sorted(directory.rglob("*.py"))


def _read_file(path):
    return path.read_text(encoding="utf-8")


# ─── Check 1: No imports inside functions ────────────────────────────────────

class ImportInsideFunctionVisitor(ast.NodeVisitor):
    def __init__(self):
        self.violations = []
        self._depth = 0

    def visit_FunctionDef(self, node):
        self._depth += 1
        self.generic_visit(node)
        self._depth -= 1

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Import(self, node):
        if self._depth > 0:
            names = ", ".join(a.name for a in node.names)
            self.violations.append((node.lineno, "import", names))
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if self._depth > 0:
            names = ", ".join(a.name for a in node.names)
            self.violations.append((node.lineno, f"from {node.module or ''}", names))
        self.generic_visit(node)


def check_imports_not_inside_functions():
    """
    Scan all .py files under /app (except app/__init__.py which unavoidably
    uses deferred blueprint imports). Report any import/from-import inside
    a function body.
    """
    failures = []
    for filepath in _collect_py_files(APP_DIR):
        if str(filepath) == str(APP_DIR / "__init__.py"):
            continue
        source = _read_file(filepath)
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            failures.append(f"{filepath.relative_to(Path.cwd())}: syntax error — {e}")
            continue
        visitor = ImportInsideFunctionVisitor()
        visitor.visit(tree)
        for lineno, kind, names in visitor.violations:
            failures.append(
                f"{filepath.relative_to(Path.cwd())}:{lineno} — {kind} '{names}' inside function"
            )
    return {"global_imports_only": len(failures) == 0, "failures": failures}


# ─── Check 2: No hardcoded English strings ───────────────────────────────────

class HardcodedStringsVisitor(ast.NodeVisitor):
    """
    Visits every jsonify(...) call and inspects the first argument if it is a dict.
    Any string-type value that is a bare Constant (not wrapped in _() or gettext)
    is flagged as a hardcoded user-facing string.
    This covers "error", "message", and any future user-facing keys.
    """

    def __init__(self):
        self.violations = []

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and node.func.id == "jsonify":
            if node.args and isinstance(node.args[0], ast.Dict):
                self._check_dict(node.args[0], node.lineno)
        self.generic_visit(node)

    def _check_dict(self, dict_node, call_lineno):
        for key_node, value_node in zip(dict_node.keys, dict_node.values):
            if not isinstance(key_node, ast.Constant):
                continue
            if not isinstance(key_node.value, str):
                continue
            if isinstance(value_node, ast.Constant) and isinstance(value_node.value, str):
                self.violations.append(
                    (call_lineno, key_node.value, value_node.value)
                )


def check_no_hardcoded_strings():
    """
    Scan route handler files for jsonify calls whose dict values are bare
    string literals instead of _()-wrapped translations.
    """
    failures = []
    for filepath in _collect_py_files(ROUTES_DIR):
        if filepath.name == "__init__.py":
            continue
        source = _read_file(filepath)
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            failures.append(f"{filepath.relative_to(Path.cwd())}: syntax error — {e}")
            continue
        visitor = HardcodedStringsVisitor()
        visitor.visit(tree)
        for lineno, key, text in visitor.violations:
            failures.append(
                f"{filepath.relative_to(Path.cwd())}:{lineno} — "
                f'hardcoded string "{text}" for key "{key}" not wrapped in _()'
            )
    return {"no_hardcoded_strings": len(failures) == 0, "failures": failures}


# ─── Check 3: Route docstrings ───────────────────────────────────────────────

_REQUIRED_SECTIONS = ("Endpoint:", "Method:", "Request body:", "Response format:")


def _is_route_decorated(func_node):
    """Return True if the function node has a @xxx.route(...) decorator."""
    for decorator in func_node.decorator_list:
        if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
            if decorator.func.attr == "route":
                return True
    return False


def check_route_docstrings():
    """
    Verify that every @blueprint.route-decorated function has a docstring
    containing all four required sections.
    """
    failures = []
    for filepath in _collect_py_files(ROUTES_DIR):
        if filepath.name == "__init__.py":
            continue
        source = _read_file(filepath)
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            failures.append(f"{filepath.relative_to(Path.cwd())}: syntax error — {e}")
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            if not _is_route_decorated(node):
                continue

            doc = ast.get_docstring(node)
            if doc is None:
                failures.append(
                    f"{filepath.relative_to(Path.cwd())}:{node.lineno} — "
                    f"function '{node.name}' has no docstring"
                )
                continue

            missing = [s for s in _REQUIRED_SECTIONS if s not in doc]
            if missing:
                failures.append(
                    f"{filepath.relative_to(Path.cwd())}:{node.lineno} — "
                    f"function '{node.name}' docstring missing: {', '.join(missing)}"
                )
    return {"route_docstrings_complete": len(failures) == 0, "failures": failures}


# ─── Check 4: Project model has __repr__ ────────────────────────────────────

def check_project_model_repr():
    """Verify the Project class in app/models/project.py defines a __repr__ method."""
    project_model = MODELS_DIR / "project.py"
    if not project_model.exists():
        return {"project_has_repr": False, "failures": ["app/models/project.py not found"]}

    source = _read_file(project_model)
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return {"project_has_repr": False, "failures": [f"Syntax error: {e}"]}

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "Project":
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "__repr__":
                    return {"project_has_repr": True, "failures": []}
            return {"project_has_repr": False, "failures": [
                "Project class in app/models/project.py has no __repr__ method"
            ]}

    return {"project_has_repr": False, "failures": [
        "No 'Project' class found in app/models/project.py"
    ]}


# ─── Check 5: No direct DB access in route handlers ─────────────────────────

def _attribute_chain(node):
    parts = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
    parts.reverse()
    return ".".join(parts)


_MODEL_QUERY_METHODS = frozenset({
    "all", "filter", "filter_by", "get", "first", "one", "one_or_none",
    "count", "order_by", "limit", "offset", "paginate", "group_by",
    "having", "join", "outerjoin", "with_entities", "add_columns",
    "from_self", "scalar", "scalars", "with_session",
})


class DirectDBCallVisitor(ast.NodeVisitor):
    """
    Flags:
      - Any 'from app import db' or 'from app.x import db' in route files
      - Any db.session.* chain (add, delete, commit, query, execute, etc.)
      - Any Model.query.<method> chain (e.g. Task.query.all())
    """

    def __init__(self):
        self.violations = []

    def visit_ImportFrom(self, node):
        if node.module and "app" in node.module and "db" in [a.name for a in node.names]:
            self.violations.append((node.lineno, f"imports db from {node.module}"))
        self.generic_visit(node)

    def visit_Attribute(self, node):
        full = _attribute_chain(node)
        if full.startswith("db.session"):
            self.violations.append((node.lineno, full))
        else:
            parts = full.split(".")
            if len(parts) >= 3 and parts[-2] == "query" and parts[-1] in _MODEL_QUERY_METHODS:
                self.violations.append((node.lineno, full))
        self.generic_visit(node)


def check_no_direct_db_in_routes():
    """
    Scan route files for direct SQLAlchemy usage: imports of 'db' from app,
    db.session.* calls, or Model.query.* calls.
    """
    failures = []
    for filepath in _collect_py_files(ROUTES_DIR):
        if filepath.name == "__init__.py":
            continue
        source = _read_file(filepath)
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            failures.append(f"{filepath.relative_to(Path.cwd())}: syntax error — {e}")
            continue
        visitor = DirectDBCallVisitor()
        visitor.visit(tree)
        seen = set()
        for lineno, what in visitor.violations:
            if (lineno, what) not in seen:
                seen.add((lineno, what))
                failures.append(
                    f"{filepath.relative_to(Path.cwd())}:{lineno} — "
                    f"direct DB access: '{what}'"
                )
    return {"no_direct_db_in_routes": len(failures) == 0, "failures": failures}


# ─── LLM Grading ─────────────────────────────────────────────────────────────

def _gather_llm_context():
    files = {}
    target_paths = [
        APP_DIR / "models" / "project.py",
        APP_DIR / "repositories" / "project_repository.py",
        APP_DIR / "routes" / "projects.py",
        APP_DIR / "models" / "task.py",
        APP_DIR / "repositories" / "task_repository.py",
        APP_DIR / "routes" / "tasks.py",
        Path.cwd() / "README.md",
    ]
    for path in target_paths:
        if path.exists():
            files[str(path.relative_to(Path.cwd()))] = _read_file(path)
    return files


def run_llm_checks(api_key=None):
    """Call the Anthropic API to score three qualitative aspects of the Projects feature."""
    if api_key is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return {
            "repository_pattern": None,
            "code_style_consistency": None,
            "api_design_consistency": None,
            "llm_evaluation_skipped": True,
            "reason": "ANTHROPIC_API_KEY not set — set the environment variable to enable LLM grading",
        }

    ctx = _gather_llm_context()

    prompt = f"""You are a senior code reviewer evaluating a Flask project's "Projects" feature for compliance with documented conventions.

Below are the relevant source files. Evaluate in three categories, each scored 0-10.

**Reference files (existing Task feature for style comparison):**
{ctx.get('app/models/task.py', 'N/A')}
{ctx.get('app/repositories/task_repository.py', 'N/A')}
{ctx.get('app/routes/tasks.py', 'N/A')}

**New Projects feature files:**
{ctx.get('app/models/project.py', 'N/A')}
{ctx.get('app/repositories/project_repository.py', 'N/A')}
{ctx.get('app/routes/projects.py', 'N/A')}

**README conventions document:**
{ctx.get('README.md', 'N/A')}

Score each category from 0 (completely fails) to 10 (perfect conformance):

1. **repository_pattern (0-10)**: Does ProjectRepository correctly extend the repository pattern? Compare against TaskRepository. Are all DB operations properly delegated? Is the pattern consistent?

2. **code_style_consistency (0-10)**: Does the new Projects code match the style of the existing Tasks code? Consider naming, formatting, parameter ordering, error handling patterns, import style, and docstring consistency.

3. **api_design_consistency (0-10)**: Are the Project endpoints consistent with the existing Task endpoints? Consider URL structure, HTTP methods used, request/response shapes, error response format, and status codes.

Return ONLY a JSON object with integer scores:
{{"repository_pattern": <int>, "code_style_consistency": <int>, "api_design_consistency": <int>}}"""

    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()

        try:
            scores = json.loads(text)
        except json.JSONDecodeError:
            scores = {}
            for field in ("repository_pattern", "code_style_consistency", "api_design_consistency"):
                m = re.search(rf'"{field}"\s*:\s*(\d+)', text)
                scores[field] = int(m.group(1)) if m else None

        return {
            "repository_pattern": scores.get("repository_pattern"),
            "code_style_consistency": scores.get("code_style_consistency"),
            "api_design_consistency": scores.get("api_design_consistency"),
        }
    except Exception as e:
        return {
            "repository_pattern": None,
            "code_style_consistency": None,
            "api_design_consistency": None,
            "llm_error": str(e),
        }


# ─── Report ──────────────────────────────────────────────────────────────────

def build_report(api_key=None):
    proc = {}

    r = check_imports_not_inside_functions()
    proc["global_imports_only"] = r["global_imports_only"]

    r = check_no_hardcoded_strings()
    proc["no_hardcoded_strings"] = r["no_hardcoded_strings"]

    r = check_route_docstrings()
    proc["route_docstrings_complete"] = r["route_docstrings_complete"]

    r = check_project_model_repr()
    proc["project_has_repr"] = r["project_has_repr"]

    r = check_no_direct_db_in_routes()
    proc["no_direct_db_in_routes"] = r["no_direct_db_in_routes"]

    failure_reasons = []
    sources = [
        ("IMPORT_IN_FUNC", check_imports_not_inside_functions),
        ("HARDCODED_STRING", check_no_hardcoded_strings),
        ("MISSING_DOCSTRING", check_route_docstrings),
        ("NO_REPR", check_project_model_repr),
        ("DIRECT_DB", check_no_direct_db_in_routes),
    ]
    for tag, fn in sources:
        result = fn()
        for f in result["failures"]:
            failure_reasons.append(f"{tag}: {f}")

    llm = run_llm_checks(api_key=api_key)

    proc_score = sum(1 for v in proc.values() if v)
    proc_max = len(proc)

    llm_checks = {
        "repository_pattern": None,
        "code_style_consistency": None,
        "api_design_consistency": None,
    }
    total_score = proc_score
    if not llm.get("llm_evaluation_skipped", False):
        for field in llm_checks:
            llm_checks[field] = llm.get(field)
            if llm.get(field) is not None:
                total_score += llm[field]
        max_possible = proc_max + 30
    else:
        max_possible = proc_max

    return {
        "procedural_checks": proc,
        "llm_checks": llm_checks,
        "total_score": total_score,
        "max_possible_score": max_possible,
        "failure_reasons": failure_reasons,
    }


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    report = build_report(api_key=api_key)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
