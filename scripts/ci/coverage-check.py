#!/usr/bin/env python3
"""
Test coverage enforcement script for CI/CD.
Parses pytest (XML) and Vitest (JSON) coverage reports, applies path-based rules,
and generates a unified markdown summary for PR comments.

Thresholds:
- Critical files: 90% (blocking)
- Non-critical files: 50% (blocking)
"""

import argparse
import json
import os
import sys
import xml.etree.ElementTree as ET
from typing import Dict, Tuple
import fnmatch


def parse_pytest_coverage(xml_path: str) -> Dict[str, Dict[str, float]]:
    """
    Parse pytest coverage XML (Cobertura format).

    Returns:
        Dict mapping filepath to {covered, total, percentage}
    """
    if not os.path.exists(xml_path):
        return {}

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        file_coverage = {}
        for package in root.findall(".//package"):
            for cls in package.findall(".//class"):
                filename = cls.get("filename")
                if not filename:
                    continue

                # Get line coverage
                lines = cls.findall(".//line")
                if not lines:
                    continue

                covered = len(
                    [line for line in lines if int(line.get("hits", "0")) > 0]
                )
                total = len(lines)
                coverage_pct = (covered / total * 100) if total > 0 else 0

                file_coverage[filename] = {
                    "covered": covered,
                    "total": total,
                    "percentage": round(coverage_pct, 1),
                }

        return file_coverage

    except ET.ParseError as e:
        print(f"Failed to parse backend coverage XML: {e}", file=sys.stderr)
        sys.exit(1)


def parse_vitest_coverage(json_path: str) -> Dict[str, Dict[str, float]]:
    """
    Parse Vitest coverage JSON (v8 format).

    Returns:
        Dict mapping filepath to {covered, total, percentage}
    """
    if not os.path.exists(json_path):
        return {}

    try:
        with open(json_path, "r") as f:
            data = json.load(f)

        file_coverage = {}
        for filepath, file_data in data.items():
            # Use statement coverage
            if "s" not in file_data:
                continue

            statements = file_data["s"]
            covered = len([v for v in statements.values() if v > 0])
            total = len(statements)
            coverage_pct = (covered / total * 100) if total > 0 else 0

            file_coverage[filepath] = {
                "covered": covered,
                "total": total,
                "percentage": round(coverage_pct, 1),
            }

        return file_coverage

    except (json.JSONDecodeError, KeyError) as e:
        print(f"Failed to parse frontend coverage JSON: {e}", file=sys.stderr)
        sys.exit(1)


def should_exclude_file(filepath: str, rules: dict) -> bool:
    """
    Check if file should be excluded from coverage checks.

    Args:
        filepath: Path to the file
        rules: Coverage rules configuration

    Returns:
        True if file should be excluded
    """
    # Determine stack
    if "frontend" in filepath or "/src/" in filepath:
        stack = "frontend"
    else:
        stack = "backend"

    if stack not in rules:
        return False

    exclude_patterns = rules[stack].get("exclude_patterns", [])
    for pattern in exclude_patterns:
        if fnmatch.fnmatch(filepath, pattern):
            return True
        # Also check just the filename
        filename = filepath.split("/")[-1]
        if fnmatch.fnmatch(filename, pattern):
            return True

    return False


def classify_file(filepath: str, rules: dict) -> Tuple[str, int]:
    """
    Classify file as 'critical' or 'default' and return threshold.

    Args:
        filepath: Path to the file
        rules: Coverage rules configuration

    Returns:
        Tuple of (classification, threshold)
    """
    # Determine stack (backend or frontend)
    if "frontend" in filepath or "/src/" in filepath:
        stack = "frontend"
    else:
        stack = "backend"

    if stack not in rules:
        return "default", 50

    stack_rules = rules[stack]

    # Check exact path matches for critical files
    critical_paths = stack_rules.get("critical_paths", [])
    for critical_path in critical_paths:
        if filepath.endswith(critical_path) or critical_path in filepath:
            return "critical", stack_rules.get("critical_threshold", 90)

    # Check glob patterns for critical files
    critical_patterns = stack_rules.get("critical_patterns", [])
    for pattern in critical_patterns:
        if fnmatch.fnmatch(filepath, pattern):
            return "critical", stack_rules.get("critical_threshold", 90)

    # Not critical, return default threshold
    return "default", stack_rules.get("default_threshold", 50)


def check_coverage(
    file_coverage: Dict[str, Dict[str, float]], rules: dict
) -> Tuple[dict, int]:
    """
    Check coverage against rules and categorize results.

    Args:
        file_coverage: Combined coverage data from both stacks
        rules: Coverage rules configuration

    Returns:
        Tuple of (results dict, exit_code)
    """
    results = {
        "critical_failures": [],  # Critical files below threshold
        "default_failures": [],  # Non-critical files below threshold
        "critical_passing": [],  # Critical files meeting threshold
        "default_passing": [],  # Non-critical files meeting threshold
    }

    for filepath, cov_data in file_coverage.items():
        # Skip excluded files (e.g., __init__.py, index.ts, .json)
        if should_exclude_file(filepath, rules):
            continue

        classification, threshold = classify_file(filepath, rules)

        if cov_data["percentage"] < threshold:
            if classification == "critical":
                results["critical_failures"].append((filepath, cov_data, threshold))
            else:
                results["default_failures"].append((filepath, cov_data, threshold))
        else:
            if classification == "critical":
                results["critical_passing"].append((filepath, cov_data, threshold))
            else:
                results["default_passing"].append((filepath, cov_data, threshold))

    # Exit code: fail if ANY files below threshold (both critical and default are blocking)
    has_failures = (
        len(results["critical_failures"]) > 0 or len(results["default_failures"]) > 0
    )
    exit_code = 1 if has_failures else 0

    return results, exit_code


def shorten_path(filepath: str) -> str:
    """Shorten filepath for display."""
    # Remove common prefixes
    if "/frontend/src/" in filepath:
        return filepath.split("/frontend/src/")[-1]
    if "/backend/app/" in filepath:
        return filepath.split("/backend/app/")[-1]
    if "app/" in filepath:
        return filepath.split("app/")[-1]
    return filepath


def generate_markdown_summary(
    results: dict,
    backend_coverage: Dict[str, Dict[str, float]],
    frontend_coverage: Dict[str, Dict[str, float]],
) -> str:
    """
    Generate concise markdown summary for PR comment.

    Shows:
    1. Summary of # files scanned (critical vs non-critical)
    2. Number of files failed threshold
    3. Table of files that fail (only failures, not all files)
    """
    # Count totals
    critical_total = len(results["critical_failures"]) + len(
        results["critical_passing"]
    )
    critical_failed = len(results["critical_failures"])

    default_total = len(results["default_failures"]) + len(results["default_passing"])
    default_failed = len(results["default_failures"])

    total_failed = critical_failed + default_failed

    # Calculate overall coverage
    backend_total_lines = sum(f["total"] for f in backend_coverage.values())
    backend_covered_lines = sum(f["covered"] for f in backend_coverage.values())
    backend_pct = (
        (backend_covered_lines / backend_total_lines * 100)
        if backend_total_lines > 0
        else 0
    )

    frontend_total_lines = sum(f["total"] for f in frontend_coverage.values())
    frontend_covered_lines = sum(f["covered"] for f in frontend_coverage.values())
    frontend_pct = (
        (frontend_covered_lines / frontend_total_lines * 100)
        if frontend_total_lines > 0
        else 0
    )

    # Determine status
    has_failures = total_failed > 0
    status_icon = "BLOCKED" if has_failures else "PASSED"
    status_emoji = "&#x274C;" if has_failures else "&#x2705;"  # Cross or checkmark

    # Build markdown
    lines = [
        "## Test Coverage Report",
        "",
        f"### {status_emoji} {status_icon}",
        "",
        "| Category | Scanned | Passed | Failed | Threshold |",
        "|----------|---------|--------|--------|-----------|",
        f"| Critical | {critical_total} | {critical_total - critical_failed} | {critical_failed} | 90% |",
        f"| Non-critical | {default_total} | {default_total - default_failed} | {default_failed} | 50% |",
        "",
        f"**Overall:** Backend {backend_pct:.1f}% | Frontend {frontend_pct:.1f}%",
        "",
    ]

    # Show failures table (only if there are failures)
    if has_failures:
        lines.append("---")
        lines.append("")
        lines.append("### Files Below Threshold")
        lines.append("")
        lines.append("| File | Coverage | Required | Type |")
        lines.append("|------|----------|----------|------|")

        # Critical failures first
        for filepath, cov_data, threshold in sorted(
            results["critical_failures"], key=lambda x: x[1]["percentage"]
        ):
            short_path = shorten_path(filepath)
            pct = cov_data["percentage"]
            lines.append(f"| `{short_path}` | {pct}% | {threshold}% | Critical |")

        # Then default failures
        for filepath, cov_data, threshold in sorted(
            results["default_failures"], key=lambda x: x[1]["percentage"]
        ):
            short_path = shorten_path(filepath)
            pct = cov_data["percentage"]
            lines.append(f"| `{short_path}` | {pct}% | {threshold}% | Non-critical |")

        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append(
            "**This PR is blocked.** All files must meet their coverage threshold."
        )
    else:
        lines.append("All files meet coverage thresholds.")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Check test coverage against rules")
    parser.add_argument("--backend", help="Path to backend coverage XML file")
    parser.add_argument("--frontend", help="Path to frontend coverage JSON file")
    parser.add_argument(
        "--rules", required=True, help="Path to coverage rules JSON file"
    )
    parser.add_argument(
        "--output", required=True, help="Path to output markdown summary file"
    )

    args = parser.parse_args()

    # Load rules
    if not os.path.exists(args.rules):
        print(f"Rules file not found: {args.rules}", file=sys.stderr)
        sys.exit(1)

    with open(args.rules, "r") as f:
        rules = json.load(f)

    # Parse coverage reports
    print("Parsing coverage reports...")

    backend_coverage = {}
    if args.backend:
        print(f"  Backend: {args.backend}")
        backend_coverage = parse_pytest_coverage(args.backend)
        if backend_coverage:
            print(f"    Found {len(backend_coverage)} files")
        else:
            print("    No backend coverage data found")

    frontend_coverage = {}
    if args.frontend:
        print(f"  Frontend: {args.frontend}")
        frontend_coverage = parse_vitest_coverage(args.frontend)
        if frontend_coverage:
            print(f"    Found {len(frontend_coverage)} files")
        else:
            print("    No frontend coverage data found")

    # Check if we have any coverage data
    if not backend_coverage and not frontend_coverage:
        print("No coverage data found. Tests may not have run.", file=sys.stderr)
        sys.exit(1)

    # Combine coverage data
    all_coverage = {**backend_coverage, **frontend_coverage}

    # Check coverage against rules
    print(f"\nChecking {len(all_coverage)} files against coverage rules...")
    results, exit_code = check_coverage(all_coverage, rules)

    # Generate markdown summary
    summary = generate_markdown_summary(results, backend_coverage, frontend_coverage)

    # Write to output file
    with open(args.output, "w") as f:
        f.write(summary)

    print(f"\nCoverage summary written to {args.output}")

    # Print results
    critical_failed = len(results["critical_failures"])
    default_failed = len(results["default_failures"])

    if critical_failed:
        print(f"\n{critical_failed} critical file(s) below 90% threshold:")
        for filepath, cov_data, threshold in results["critical_failures"]:
            print(f"  - {shorten_path(filepath)}: {cov_data['percentage']}%")

    if default_failed:
        print(f"\n{default_failed} non-critical file(s) below 50% threshold:")
        for filepath, cov_data, threshold in results["default_failures"]:
            print(f"  - {shorten_path(filepath)}: {cov_data['percentage']}%")

    if not critical_failed and not default_failed:
        print("\nAll files meet coverage thresholds")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
