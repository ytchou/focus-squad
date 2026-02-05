#!/usr/bin/env python3
"""
Test coverage enforcement script for CI/CD.
Parses pytest (XML) and Vitest (JSON) coverage reports, applies path-based rules,
and generates a unified markdown summary for PR comments.
"""

import argparse
import json
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Tuple, Optional
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
        for package in root.findall('.//package'):
            for cls in package.findall('.//class'):
                filename = cls.get('filename')
                if not filename:
                    continue

                # Get line coverage
                lines = cls.findall('.//line')
                if not lines:
                    continue

                covered = len([l for l in lines if int(l.get('hits', '0')) > 0])
                total = len(lines)
                coverage_pct = (covered / total * 100) if total > 0 else 0

                file_coverage[filename] = {
                    'covered': covered,
                    'total': total,
                    'percentage': round(coverage_pct, 1)
                }

        return file_coverage

    except ET.ParseError as e:
        print(f"❌ Failed to parse backend coverage XML: {e}", file=sys.stderr)
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
        with open(json_path, 'r') as f:
            data = json.load(f)

        file_coverage = {}
        for filepath, file_data in data.items():
            # Use statement coverage
            if 's' not in file_data:
                continue

            statements = file_data['s']
            covered = len([v for v in statements.values() if v > 0])
            total = len(statements)
            coverage_pct = (covered / total * 100) if total > 0 else 0

            file_coverage[filepath] = {
                'covered': covered,
                'total': total,
                'percentage': round(coverage_pct, 1)
            }

        return file_coverage

    except (json.JSONDecodeError, KeyError) as e:
        print(f"❌ Failed to parse frontend coverage JSON: {e}", file=sys.stderr)
        sys.exit(1)


def classify_file(filepath: str, rules: dict) -> Tuple[str, int]:
    """
    Classify file as 'critical' or 'warning' and return threshold.

    Args:
        filepath: Path to the file
        rules: Coverage rules configuration

    Returns:
        Tuple of (classification, threshold)
    """
    # Determine stack (backend or frontend)
    # Frontend files have absolute paths or contain 'frontend' or 'src/stores'
    # Backend files are relative paths from app/ directory
    if 'frontend' in filepath or '/src/' in filepath:
        stack = 'frontend'
    else:
        stack = 'backend'

    if stack not in rules:
        # Default to warning threshold if stack not in rules
        return 'warning', 70

    stack_rules = rules[stack]

    # Check exact path matches for critical files
    critical_paths = stack_rules.get('critical_paths', [])
    if filepath in critical_paths:
        return 'critical', stack_rules['critical_threshold']

    # Check glob patterns for critical files
    critical_patterns = stack_rules.get('critical_patterns', [])
    for pattern in critical_patterns:
        if fnmatch.fnmatch(filepath, pattern):
            return 'critical', stack_rules['critical_threshold']

    # Not critical, return warning threshold
    return 'warning', stack_rules.get('warning_threshold', 70)


def check_coverage(
    file_coverage: Dict[str, Dict[str, float]],
    rules: dict
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
        'critical_failures': [],  # Critical files below threshold
        'warnings': [],           # Non-critical files below threshold
        'passing': []             # Files meeting threshold
    }

    for filepath, cov_data in file_coverage.items():
        classification, threshold = classify_file(filepath, rules)

        if cov_data['percentage'] < threshold:
            if classification == 'critical':
                results['critical_failures'].append((filepath, cov_data, threshold))
            else:
                results['warnings'].append((filepath, cov_data, threshold))
        else:
            results['passing'].append((filepath, cov_data, threshold))

    # Exit code: fail only if critical files below threshold
    exit_code = 1 if results['critical_failures'] else 0

    return results, exit_code


def generate_markdown_summary(
    results: dict,
    backend_coverage: Dict[str, Dict[str, float]],
    frontend_coverage: Dict[str, Dict[str, float]]
) -> str:
    """
    Generate markdown summary for PR comment.

    Args:
        results: Categorized coverage results
        backend_coverage: Backend coverage data
        frontend_coverage: Frontend coverage data

    Returns:
        Markdown formatted string
    """
    # Calculate overall coverage
    backend_total_lines = sum(f['total'] for f in backend_coverage.values())
    backend_covered_lines = sum(f['covered'] for f in backend_coverage.values())
    backend_pct = (backend_covered_lines / backend_total_lines * 100) if backend_total_lines > 0 else 0

    frontend_total_lines = sum(f['total'] for f in frontend_coverage.values())
    frontend_covered_lines = sum(f['covered'] for f in frontend_coverage.values())
    frontend_pct = (frontend_covered_lines / frontend_total_lines * 100) if frontend_total_lines > 0 else 0

    # Determine status
    has_failures = len(results['critical_failures']) > 0
    status = "❌ BLOCKED" if has_failures else "✅ PASSED"
    status_message = (
        "Critical files must meet 80% coverage threshold."
        if has_failures
        else "All critical files meet coverage thresholds."
    )

    # Build markdown
    lines = [
        "## 📊 Test Coverage Report",
        "",
        f"### {status}",
        status_message,
        "",
        "---",
        ""
    ]

    # Critical files section
    lines.append("### 🔴 Critical Files (80% required)")

    if results['critical_failures'] or any(t == 80 for f, d, t in results['passing']):
        lines.append("| File | Coverage | Status |")
        lines.append("|------|----------|--------|")

        # Show failures first
        for filepath, cov_data, threshold in results['critical_failures']:
            pct = cov_data['percentage']
            lines.append(f"| `{filepath}` | {pct}% | ⚠️ **BELOW THRESHOLD** |")

        # Show passing critical files
        for filepath, cov_data, threshold in results['passing']:
            classification, _ = classify_file(filepath, {})  # We already know it's passing
            if threshold == 80:  # Critical threshold
                pct = cov_data['percentage']
                lines.append(f"| `{filepath}` | {pct}% | ✅ Pass |")
    else:
        lines.append("*No critical files found in coverage report.*")

    lines.append("")

    # Warnings section
    if results['warnings']:
        lines.append("### ⚠️ Warnings (70% required)")
        lines.append("| File | Coverage | Status |")
        lines.append("|------|----------|--------|")

        for filepath, cov_data, threshold in results['warnings']:
            pct = cov_data['percentage']
            lines.append(f"| `{filepath}` | {pct}% | ⚠️ Below threshold |")

        lines.append("")

    # Summary section
    critical_passing = len([f for f, d, t in results['passing'] if t == 80])
    critical_total = critical_passing + len(results['critical_failures'])

    other_passing = len([f for f, d, t in results['passing'] if t != 80])
    other_total = other_passing + len(results['warnings'])

    lines.extend([
        "### 📈 Summary",
        f"- **Critical files:** {critical_passing}/{critical_total} passing (80% required)",
        f"- **Other files:** {other_passing}/{other_total} above 70%",
        f"- **Overall coverage:** Backend {backend_pct:.1f}% | Frontend {frontend_pct:.1f}%",
        ""
    ])

    # Final status message
    if has_failures:
        lines.append("---")
        lines.append("❌ **This PR is blocked.** Critical files must meet 80% coverage threshold.")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Check test coverage against rules")
    parser.add_argument("--backend", help="Path to backend coverage XML file")
    parser.add_argument("--frontend", help="Path to frontend coverage JSON file")
    parser.add_argument("--rules", required=True, help="Path to coverage rules JSON file")
    parser.add_argument("--output", required=True, help="Path to output markdown summary file")

    args = parser.parse_args()

    # Load rules
    if not os.path.exists(args.rules):
        print(f"❌ Rules file not found: {args.rules}", file=sys.stderr)
        sys.exit(1)

    with open(args.rules, 'r') as f:
        rules = json.load(f)

    # Parse coverage reports
    print("📊 Parsing coverage reports...")

    backend_coverage = {}
    if args.backend:
        print(f"  Backend: {args.backend}")
        backend_coverage = parse_pytest_coverage(args.backend)
        if backend_coverage:
            print(f"    ✓ Found {len(backend_coverage)} files")
        else:
            print("    ⚠️ No backend coverage data found")

    frontend_coverage = {}
    if args.frontend:
        print(f"  Frontend: {args.frontend}")
        frontend_coverage = parse_vitest_coverage(args.frontend)
        if frontend_coverage:
            print(f"    ✓ Found {len(frontend_coverage)} files")
        else:
            print("    ⚠️ No frontend coverage data found")

    # Check if we have any coverage data
    if not backend_coverage and not frontend_coverage:
        print("❌ No coverage data found. Tests may not have run.", file=sys.stderr)
        sys.exit(1)

    # Combine coverage data
    all_coverage = {**backend_coverage, **frontend_coverage}

    # Check coverage against rules
    print(f"\n🔍 Checking {len(all_coverage)} files against coverage rules...")
    results, exit_code = check_coverage(all_coverage, rules)

    # Generate markdown summary
    summary = generate_markdown_summary(results, backend_coverage, frontend_coverage)

    # Write to output file
    with open(args.output, 'w') as f:
        f.write(summary)

    print(f"\n✓ Coverage summary written to {args.output}")

    # Print results
    if results['critical_failures']:
        print(f"\n❌ {len(results['critical_failures'])} critical file(s) below threshold")
        for filepath, cov_data, threshold in results['critical_failures']:
            print(f"  - {filepath}: {cov_data['percentage']}% (needs {threshold}%)")

    if results['warnings']:
        print(f"\n⚠️  {len(results['warnings'])} file(s) below warning threshold")

    if not results['critical_failures']:
        print("\n✅ All critical files meet coverage thresholds")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
