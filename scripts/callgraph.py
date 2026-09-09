#!/usr/bin/env python3
"""
callgraph.py — work out what calls what, and write it down.

    python scripts/callgraph.py            # regenerate docs/CALLGRAPH.md
    python scripts/callgraph.py --check    # fail if a layering rule is broken
    python scripts/callgraph.py --route /api/quiz

Why this exists rather than Doxygen: Doxygen understands C++ and treats
Python as an afterthought, and its call graphs need Graphviz to render to
images nobody can read in a pull request.  This walks the AST instead and
emits Mermaid, which GitHub renders inline — so the diagram lives in the
repository, reviews show its diff, and nothing has to be installed.

Three outputs, aimed at three real questions:

  "How is this thing put together?"   → the module graph
  "If I change this route, what
   does it touch?"                    → the route table
  "Did I just wire it up backwards?"  → the layering check

The last one is the useful one in CI.  This codebase has a deliberate
direction of dependency — routes call services call data, never the
reverse — and that is easy to break by accident and invisible in review.
"""

from __future__ import annotations

import argparse
import ast
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PACKAGE = REPO / "game"

# The intended shape of the application, from the outside in. A module may
# depend on anything in a LOWER layer, never a higher one — so db.py must
# never import app.py, and billing.py must never reach for a request.
LAYERS: list[tuple[str, list[str]]] = [
    ("entrypoint", ["wsgi", "manage", "migrate_json", "import_assets",
                    "selftest", "selftest_billing", "selftest_classrooms",
                    "selftest_accounts", "selftest_standards",
                    "selftest_gating", "selftest_resources"]),
    ("web",        ["app"]),
    ("service",    ["billing", "security", "emailer", "tracks", "standards"]),
    ("data",       ["db"]),
    ("platform",   ["config", "logsetup"]),
]

LAYER_OF = {module: index for index, (_, modules) in enumerate(LAYERS) for module in modules}
LAYER_NAME = {index: name for index, (name, _) in enumerate(LAYERS)}

# Third-party and stdlib names are noise in an internal call graph.
LOCAL_MODULES = set(LAYER_OF)


class Module:
    """One parsed source file."""

    def __init__(self, path: Path):
        self.path = path
        self.name = path.stem
        self.tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        self.imports: set[str] = set()
        self.functions: dict[str, Function] = {}
        self.routes: list[Route] = []
        self._walk()

    def _walk(self) -> None:
        for node in self.tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.imports.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.level == 0:
                    self.imports.add(node.module.split(".")[0])
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._add_function(node)
            elif isinstance(node, ast.ClassDef):
                for sub in node.body:
                    if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        self._add_function(sub, prefix=f"{node.name}.")

    def _add_function(self, node, prefix: str = "") -> None:
        function = Function(self.name, prefix + node.name, node)
        self.functions[function.name] = function
        if function.route_paths:
            self.routes.append(Route(function))


class Function:
    """One function, its decorators, and the calls in its body."""

    def __init__(self, module: str, name: str, node):
        self.module = module
        self.name = name
        self.node = node
        self.lineno = node.lineno
        self.doc = (ast.get_docstring(node) or "").strip()
        self.decorators = [self._decorator_name(d) for d in node.decorator_list]
        self.route_paths: list[str] = []
        self.methods: list[str] = []
        self.calls: set[tuple[str, str]] = set()   # (module_or_"", function)
        self._read_routes(node)
        self._read_calls(node)

    @staticmethod
    def _decorator_name(node) -> str:
        target = node.func if isinstance(node, ast.Call) else node
        parts = []
        while isinstance(target, ast.Attribute):
            parts.append(target.attr)
            target = target.value
        if isinstance(target, ast.Name):
            parts.append(target.id)
        return ".".join(reversed(parts))

    def _read_routes(self, node) -> None:
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            if self._decorator_name(decorator) not in ("app.route", "route"):
                continue
            for arg in decorator.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    self.route_paths.append(arg.value)
            for keyword in decorator.keywords:
                if keyword.arg == "methods" and isinstance(keyword.value, (ast.List, ast.Tuple)):
                    self.methods = [e.value for e in keyword.value.elts
                                    if isinstance(e, ast.Constant)]
        if self.route_paths and not self.methods:
            self.methods = ["GET"]

    def _read_calls(self, node) -> None:
        for child in ast.walk(node):
            if not isinstance(child, ast.Call):
                continue
            target = child.func
            if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name):
                # db.foo(), billing.bar()
                self.calls.add((target.value.id, target.attr))
            elif isinstance(target, ast.Name):
                # a helper defined in this same module
                self.calls.add(("", target.id))

    @property
    def qualified(self) -> str:
        return f"{self.module}.{self.name}"

    @property
    def summary(self) -> str:
        """First sentence of the docstring, for a table cell."""
        if not self.doc:
            return ""
        first = self.doc.split("\n\n")[0].replace("\n", " ").strip()
        for stop in (". ", "? ", "! "):
            if stop in first:
                first = first.split(stop)[0] + stop.strip()
                break
        return first[:110]


class Route:
    def __init__(self, function: Function):
        self.function = function
        self.paths = function.route_paths
        self.methods = function.methods

    GUARDS = {
        "login_required":      "signed in",
        "membership_required": "approved member",
        "org_admin_required":  "org admin",
        "csrf_exempt":         "CSRF exempt",
    }

    @property
    def guards(self) -> list[str]:
        found = []
        for decorator in self.function.decorators:
            plain = decorator.split(".")[-1]
            if plain in self.GUARDS:
                found.append(self.GUARDS[plain])
        return found


def load_modules() -> dict[str, Module]:
    modules = {}
    for path in sorted(PACKAGE.glob("*.py")):
        if path.stem.startswith("_"):
            continue
        try:
            modules[path.stem] = Module(path)
        except SyntaxError as exc:
            print(f"  ! {path.name}: {exc}", file=sys.stderr)
    return modules


# ── Layering ────────────────────────────────────────────────────────────────────

def layer_violations(modules: dict[str, Module]) -> list[tuple[str, str]]:
    """
    Imports that point the wrong way through the layers.

    A module may depend on a lower layer, never a higher one. Catching this
    mechanically matters because the mistake is invisible in review: a
    single `import app` inside db.py reads as harmless and quietly turns
    two layers into one.
    """
    bad = []
    for name, module in modules.items():
        if name not in LAYER_OF:
            # Not placed in a layer, so nothing can be checked about it.
            # Reported rather than skipped: a new module quietly escaping
            # the layering rules is exactly what this is here to prevent.
            bad.append((name, "<unplaced: add it to LAYERS>"))
            continue
        for imported in module.imports & LOCAL_MODULES:
            if imported == name:
                continue
            if LAYER_OF[imported] < LAYER_OF[name]:
                bad.append((name, imported))
    return sorted(bad)


def external_reach(modules: dict[str, Module], function: Function,
                   depth: int = 3) -> set[tuple[str, str]]:
    """
    Which other modules this function ends up touching.

    Local helper calls are followed (up to `depth`) and cross-module calls
    collected, so a route reports what it *reaches* rather than only what
    its own body names. That is the question you actually have when
    changing a handler.
    """
    seen_local: set[str] = set()
    reached: set[tuple[str, str]] = set()
    frontier = [(function, 0)]

    while frontier:
        current, level = frontier.pop()
        for module_name, call_name in current.calls:
            # Skip a name matching the module we are already in: inside
            # app.py, `app.route(...)` is the Flask object, not the module.
            if module_name in LOCAL_MODULES and module_name != function.module:
                reached.add((module_name, call_name))
            elif module_name == "" and level < depth:
                helper = modules[current.module].functions.get(call_name)
                if helper and helper.qualified not in seen_local:
                    seen_local.add(helper.qualified)
                    frontier.append((helper, level + 1))
    return reached


# ── Rendering ───────────────────────────────────────────────────────────────────

def mermaid_module_graph(modules: dict[str, Module]) -> str:
    lines = ["```mermaid", "graph TD"]
    for index, (layer_name, members) in enumerate(LAYERS):
        present = [m for m in members if m in modules]
        if not present:
            continue
        lines.append(f'    subgraph L{index}["{layer_name}"]')
        for member in present:
            lines.append(f'        {member}["{member}.py"]')
        lines.append("    end")

    edges = set()
    for name, module in modules.items():
        if name not in LAYER_OF:
            continue
        for imported in sorted(module.imports & LOCAL_MODULES):
            if imported != name:
                edges.add((name, imported))
    for source, target in sorted(edges):
        lines.append(f"    {source} --> {target}")
    lines.append("```")
    return "\n".join(lines)


def route_rows(modules: dict[str, Module]) -> list[dict]:
    rows = []
    for module in modules.values():
        for route in module.routes:
            reached = external_reach(modules, route.function)
            touches = sorted({m for m, _ in reached})
            rows.append({
                "path":    route.paths[0],
                "methods": "/".join(route.methods),
                "handler": route.function.qualified,
                "line":    route.function.lineno,
                "guards":  route.guards,
                "touches": touches,
                "calls":   sorted(reached),
                "summary": route.function.summary,
            })
    return sorted(rows, key=lambda r: r["path"])


def render(modules: dict[str, Module]) -> str:
    rows = route_rows(modules)
    violations = layer_violations(modules)

    out = [
        "# Call graph",
        "",
        "**Generated — do not edit.** Regenerate with `python scripts/callgraph.py`",
        "after changing routes or module imports.",
        "",
        "Built by walking the AST of everything in `game/`. It answers three",
        "questions: how the modules stack up, what a given route touches, and",
        "whether anything is wired backwards.",
        "",
        "---",
        "",
        "## Module layers",
        "",
        "Dependencies run downward only. A module may use anything in a layer",
        "below it and nothing above — routes call services, services call data,",
        "and nothing calls back up.",
        "",
        mermaid_module_graph(modules),
        "",
    ]

    if violations:
        out += ["### ⚠ Layering violations", ""]
        out += [(f"- `{source}.py` is not placed in a layer — add it to `LAYERS`"
                 if target.startswith("<") else
                 f"- `{source}.py` imports `{target}.py` "
                 f"({LAYER_NAME[LAYER_OF[source]]} → {LAYER_NAME[LAYER_OF[target]]})")
                for source, target in violations]
        out += [""]
    else:
        out += ["No layering violations: every import points downward.", ""]

    out += ["---", "", "## Routes", "",
            f"{len(rows)} routes. **Guards** are the decorators that must pass before",
            "the handler runs; **touches** is every other module the handler reaches,",
            "following local helpers.", "",
            "| Route | Methods | Guards | Handler | Touches |",
            "|---|---|---|---|---|"]

    for row in rows:
        guards = ", ".join(row["guards"]) or "—"
        touches = ", ".join(f"`{t}`" for t in row["touches"]) or "—"
        out.append(f"| `{row['path']}` | {row['methods']} | {guards} | "
                   f"`{row['handler']}` | {touches} |")

    out += ["", "---", "", "## What each route calls", "",
            "Expanded one level through local helpers, so this is what the",
            "handler ultimately reaches — not just what its own body names.", ""]

    for row in rows:
        if not row["calls"]:
            continue
        out += [f"### `{row['methods']} {row['path']}`", ""]
        if row["summary"]:
            out += [f"{row['summary']}", ""]
        out += [f"`{row['handler']}` — game/{row['handler'].split('.')[0]}.py:{row['line']}", ""]
        by_module = defaultdict(list)
        for module_name, call_name in row["calls"]:
            by_module[module_name].append(call_name)
        for module_name in sorted(by_module):
            names = ", ".join(f"`{n}`" for n in sorted(set(by_module[module_name])))
            out += [f"- **{module_name}** → {names}"]
        out += [""]

    out += ["---", "", "## Module summary", "",
            "| Module | Layer | Functions | Routes | Imports |",
            "|---|---|---|---|---|"]
    for name in sorted(modules, key=lambda n: (LAYER_OF.get(n, 99), n)):
        module = modules[name]
        layer = LAYER_NAME.get(LAYER_OF.get(name, -1), "—")
        local_imports = sorted(module.imports & LOCAL_MODULES - {name})
        out.append(f"| `{name}.py` | {layer} | {len(module.functions)} | "
                   f"{len(module.routes)} | "
                   f"{', '.join(f'`{i}`' for i in local_imports) or '—'} |")
    out.append("")
    return "\n".join(out)


def describe_route(modules: dict[str, Module], wanted: str) -> int:
    matches = [r for r in route_rows(modules) if wanted in r["path"]]
    if not matches:
        print(f"No route matching {wanted!r}.", file=sys.stderr)
        return 1
    for row in matches:
        print(f"\n  {row['methods']} {row['path']}")
        print(f"    handler  {row['handler']}  (line {row['line']})")
        print(f"    guards   {', '.join(row['guards']) or 'none'}")
        if row["summary"]:
            print(f"    does     {row['summary']}")
        print("    calls")
        by_module = defaultdict(list)
        for module_name, call_name in row["calls"]:
            by_module[module_name].append(call_name)
        for module_name in sorted(by_module):
            for call_name in sorted(set(by_module[module_name])):
                print(f"      {module_name}.{call_name}")
    print()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true",
                        help="Exit non-zero if a layering rule is broken. For CI.")
    parser.add_argument("--route", help="Describe one route instead of writing the file.")
    parser.add_argument("-o", "--out", default="docs/CALLGRAPH.md")
    args = parser.parse_args()

    modules = load_modules()
    if not modules:
        print(f"No modules found under {PACKAGE}", file=sys.stderr)
        return 1

    if args.route:
        return describe_route(modules, args.route)

    if args.check:
        violations = layer_violations(modules)
        for source, target in violations:
            if target.startswith("<"):
                print(f"  {source}.py is not placed in a layer {target}", file=sys.stderr)
                continue
            print(f"  layering violation: {source}.py imports {target}.py "
                  f"({LAYER_NAME[LAYER_OF[source]]} → {LAYER_NAME[LAYER_OF[target]]})",
                  file=sys.stderr)
        if violations:
            return 1
        print(f"  {len(modules)} modules, no layering violations.")
        return 0

    target = REPO / args.out
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render(modules), encoding="utf-8")
    routes = sum(len(m.routes) for m in modules.values())
    print(f"  wrote {args.out} — {len(modules)} modules, {routes} routes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
