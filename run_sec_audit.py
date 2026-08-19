"""Fail-closed static checks for CAOS HTTP route authentication boundaries.

This intentionally checks the concrete dependency names used by the service.  A
generic ``Depends(...)`` is not proof of authentication, and a parser failure is
itself a failed audit rather than a reason to silently skip a module.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parent
SERVER = ROOT / "caos" / "server"
HTTP_METHODS = {"delete", "get", "head", "options", "patch", "post", "put"}
IDENTITY_DEPENDENCIES = {"get_identity", "get_write_identity"}

# These handlers intentionally establish or clear identity, or are the service
# liveness endpoint.  Keep this allowlist handler-exact so a new endpoint in the
# same module cannot inherit an exemption by filename.
ALLOWLIST: frozenset[tuple[str, str]] = frozenset(
    {
        ("caos/server/routes/auth.py", "create_profile"),
        ("caos/server/routes/auth.py", "register"),
        ("caos/server/routes/auth.py", "login"),
        ("caos/server/routes/auth.py", "recover_login"),
        ("caos/server/routes/auth.py", "logout"),
        ("caos/server/routes/health.py", "health"),
    }
)


def _symbol(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _route_method(decorator: ast.AST) -> str | None:
    call = decorator if isinstance(decorator, ast.Call) else None
    if call is None or not isinstance(call.func, ast.Attribute):
        return None
    method = call.func.attr.lower()
    return method if method in HTTP_METHODS else None


def _is_identity_dependency(node: ast.AST | None) -> bool:
    if not isinstance(node, ast.Call) or _symbol(node.func) != "Depends" or not node.args:
        return False
    dependency = node.args[0]
    if _symbol(dependency) in IDENTITY_DEPENDENCIES:
        return True
    return isinstance(dependency, ast.Call) and _symbol(dependency.func) == "require_role"


def _router_has_identity_dependency(tree: ast.Module, router_name: str) -> bool:
    for node in tree.body:
        targets: list[ast.expr] = []
        value: ast.AST | None = None
        if isinstance(node, ast.Assign):
            targets, value = node.targets, node.value
        elif isinstance(node, ast.AnnAssign):
            targets, value = [node.target], node.value
        if not any(isinstance(target, ast.Name) and target.id == router_name for target in targets):
            continue
        if not isinstance(value, ast.Call) or _symbol(value.func) != "APIRouter":
            continue
        for keyword in value.keywords:
            if keyword.arg != "dependencies" or not isinstance(keyword.value, (ast.List, ast.Tuple)):
                continue
            if any(_is_identity_dependency(element) for element in keyword.value.elts):
                return True
    return False


def _handler_has_identity(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    arguments = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
    if any(_symbol(argument.annotation) == "CallerIdentity" for argument in arguments):
        return True
    defaults: Iterable[ast.AST | None] = [*node.args.defaults, *node.args.kw_defaults]
    return any(_is_identity_dependency(default) for default in defaults)


def scan_file(path: Path, *, allowlist: frozenset[tuple[str, str]] = ALLOWLIST) -> list[dict[str, object]]:
    relative = path.resolve().relative_to(ROOT).as_posix()
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
    except (OSError, SyntaxError, UnicodeError) as exc:
        return [{
            "file": relative,
            "severity": "high",
            "lens": "availability",
            "summary": f"Security audit could not parse route module: {exc}",
        }]

    findings: list[dict[str, object]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        route_decorators = [decorator for decorator in node.decorator_list if _route_method(decorator)]
        if not route_decorators or (relative, node.name) in allowlist:
            continue
        routers = {
            decorator.func.value.id
            for decorator in route_decorators
            if isinstance(decorator, ast.Call)
            and isinstance(decorator.func, ast.Attribute)
            and isinstance(decorator.func.value, ast.Name)
        }
        if _handler_has_identity(node) or any(
            _router_has_identity_dependency(tree, router) for router in routers
        ):
            continue
        findings.append({
            "file": relative,
            "line": node.lineno,
            "severity": "high",
            "lens": "authentication",
            "summary": f"Route handler {node.name} has no approved caller-identity dependency.",
        })
    return findings


def route_files() -> list[Path]:
    return [
        *sorted((SERVER / "routes").glob("*.py")),
        SERVER / "main.py",
        SERVER / "identity.py",
    ]


def main() -> int:
    findings = [finding for path in route_files() for finding in scan_file(path)]
    print(json.dumps(findings, indent=2, sort_keys=True))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
