#!/usr/bin/env python3
"""Modular OS taxonomy consistency check (TAXONOMY_RECONCILIATION.md §5).

The canonical module_name (Taxonomy A) is encoded in each payload-schema filename
(CP-XX__<ModuleName>__payload.schema.txt) and is authoritative per the owner-ratified
reconciliation. This asserts that same name appears in every place that must agree:

  (a) the schema body            (b) the module ACTIVE_PROMPT
  (c) CP-X/SYSTEM_REFERENCE.md   (the routing source of truth)
  (d) the onboarding doc module table

Names are normalized (alphanumeric, lowercase). A miss in (c)/(d) is taxonomy drift
that degrades CP-X routing in the Copilot deployment.

Run: python3 "Modular OS/tools/check_module_consistency.py"
Exit 0 = consistent; exit 1 = drift (suitable as a CI gate).

ponytail: stdlib only, filename-anchored substring match across 4 sources.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]  # Modular OS/
PAYLOADS = ROOT / "KNOWLEDGE SOURCES" / "02_SCHEMA" / "MODULE_PAYLOADS"
CPX_ROUTE = ROOT / "CP-X" / "SYSTEM_REFERENCE.md"
ONBOARDING = ROOT / "README" / "CP_ONBOARDING_DOCUMENTATION_v2.txt"
ROUTE_GRAPH = ROOT / "KNOWLEDGE SOURCES" / "03_ORCHESTRATION" / "CP-X_ROUTE_GRAPH_v2.2.txt"
ROUTING_INDEX = ROOT / "KNOWLEDGE SOURCES" / "03_ORCHESTRATION" / "CP_ROUTING_INDEX_v2.2.txt"
COMMON_PREAMBLE = ROOT / "KNOWLEDGE SOURCES" / "00_GOVERNANCE" / "CP-COMMON_PREAMBLE.md"


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def read(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace") if p.is_file() else ""


def prompt_text(code: str) -> str:
    d = ROOT / code
    hits = list(d.glob("*ACTIVE_PROMPT.md")) if d.is_dir() else []
    return read(hits[0]) if hits else ""


def row_for(code: str, text: str) -> str:
    """The markdown table row whose FIRST cell is exactly this CP code."""
    for line in text.splitlines():
        if "|" not in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells and cells[0] == code:
            return line
    return ""


def main() -> int:
    route_txt, onboard_txt = read(CPX_ROUTE), read(ONBOARDING)
    fails, checked = [], 0
    for sp in sorted(PAYLOADS.glob("*__payload.schema.txt")):
        code, canon = sp.name.split("__", 2)[0], sp.name.split("__", 2)[1]
        nc = norm(canon)
        checked += 1
        miss = []
        if nc not in norm(read(sp)):
            miss.append("schema")
        if nc not in norm(prompt_text(code)):
            miss.append("ACTIVE_PROMPT")
        # (c)/(d): only flag when the doc lists the code at all (CP-X table omits L5/L7)
        rrow = row_for(code, route_txt)
        if rrow and nc not in norm(rrow):
            wrong = rrow.split("|")[2].strip() if rrow.count("|") >= 2 else "?"
            miss.append(f"CP-X-route(has '{wrong}')")
        orow = row_for(code, onboard_txt)
        if orow and nc not in norm(orow):
            miss.append("onboarding")
        if miss:
            fails.append(f"{code} ({canon}): drift in {', '.join(miss)}")

    for f in fails:
        print(f"DRIFT {f}")
    # Phase-4 modules are independently flagged at runtime, but every canonical
    # route/reference surface must still know their exact IDs and names.
    for code in ("CP-2G", "CP-4D"):
        for label, path in (
            ("route-graph", ROUTE_GRAPH),
            ("routing-index", ROUTING_INDEX),
            ("common-preamble", COMMON_PREAMBLE),
        ):
            if code not in read(path):
                fails.append(f"{code}: missing from {label}")

    # Print Phase-4 checks after the original taxonomy rows too.
    for f in fails:
        if f.startswith(("CP-2G:", "CP-4D:")):
            print(f"DRIFT {f}")
    print(f"\n{checked} modules checked, {len(fails)} with drift.")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
