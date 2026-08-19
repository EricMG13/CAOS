def main() -> int:
    args = _arguments()
    baseline_path = args.baseline if args.baseline.is_absolute() else REPO_ROOT / args.baseline
    try:
        changed_paths = _changed_python_paths(args.base_ref)
        baseline = _load_baseline(baseline_path)
        findings = _run_ruff(changed_paths, args.ruff)
        problems = _assess_findings(findings, baseline, changed_paths)
    except (GateError, OSError) as exc:
        print(f"complexity gate error: {exc}", file=sys.stderr)
        return 2
    if problems:
        print("Complexity delta gate failed:")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print(
        "Complexity delta gate passed: "
        f"{len(findings)} bounded finding(s) across {len(changed_paths)} changed Python path(s)."
    )
    return 0
