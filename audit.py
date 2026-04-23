#!/usr/bin/env python3

import json
import os
from collections import Counter, defaultdict
from statistics import mean
from typing import Any


def load_runs(file_path: str) -> list[dict[str, Any]]:
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict) and "runs" in data:
        runs = data["runs"]
    elif isinstance(data, list):
        runs = data
    else:
        raise ValueError("Input JSON must be a list of runs or an object with a 'runs' key.")

    if not isinstance(runs, list):
        raise ValueError("'runs' must be a list.")

    return runs


def normalize_step_type(step: dict[str, Any]) -> str:
    return step.get("type", "unknown").strip().lower()


def extract_failure_reasons(run: dict[str, Any]) -> list[str]:
    reasons = []

    for step in run.get("steps", []):
        result = str(step.get("result", "")).strip().lower()
        if result == "fail":
            reason = step.get("reason", "unknown")
            reasons.append(str(reason).strip())

    return reasons


def build_path_signature(run: dict[str, Any]) -> str:
    parts = []

    for step in run.get("steps", []):
        step_type = normalize_step_type(step).upper()
        result = str(step.get("result", "")).strip().lower()

        if result == "pass":
            parts.append(f"{step_type}_PASS")
        elif result == "fail":
            parts.append(f"{step_type}_FAIL")
        else:
            parts.append(step_type)

    return " -> ".join(parts) if parts else "NO_STEPS"

def is_success(run: dict[str, Any]) -> bool:
    return str(run.get("final_status", "")).strip().lower() == "success"


def has_retry(run: dict[str, Any]) -> bool:
    return any(normalize_step_type(step) == "retry" for step in run.get("steps", []))


def get_step_count(run: dict[str, Any]) -> int:
    return len(run.get("steps", []))


def find_golden_path(runs: list[dict[str, Any]]) -> str:
    successful_runs = [run for run in runs if is_success(run)]
    if not successful_runs:
        return "NO_SUCCESSFUL_PATH"

    grouped_by_signature: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for run in successful_runs:
        signature = build_path_signature(run)
        grouped_by_signature[signature].append(run)

    # Rank by:
    # 1. Fewest steps
    # 2. Highest frequency
    # 3. Shortest string as final tiebreaker
    ranked = sorted(
        grouped_by_signature.items(),
        key=lambda item: (
            min(get_step_count(run) for run in item[1]),
            -len(item[1]),
            len(item[0]),
        ),
    )

    return ranked[0][0]


def analyze_runs(runs: list[dict[str, Any]]) -> dict[str, Any]:
    if not runs:
        raise ValueError("No runs found in input.")

    total_runs = len(runs)
    successful_runs = [run for run in runs if is_success(run)]
    failed_runs = [run for run in runs if not is_success(run)]

    success_count = len(successful_runs)
    failure_count = len(failed_runs)

    retry_count = sum(1 for run in runs if has_retry(run))
    step_counts = [get_step_count(run) for run in runs]

    failure_reason_counter = Counter()
    for run in runs:
        failure_reason_counter.update(extract_failure_reasons(run))

    path_counter = Counter(build_path_signature(run) for run in runs)
    golden_path = find_golden_path(runs)
    golden_path_deviation_count = sum(
        1 for run in runs if build_path_signature(run) != golden_path
    )

    success_rate = success_count / total_runs
    failure_rate = failure_count / total_runs
    retry_rate = retry_count / total_runs
    average_steps = mean(step_counts) if step_counts else 0.0
    golden_path_deviation_rate = golden_path_deviation_count / total_runs

    suggestions = []

    if retry_rate >= 0.30:
        suggestions.append(
            "High retry rate detected. The initial prompt or first-pass logic may be under-specified."
        )

    if average_steps > 3:
        suggestions.append(
            "Average trajectory length is high. Review whether the workflow includes avoidable validation/retry loops."
        )

    if failure_reason_counter:
        top_reason, top_count = failure_reason_counter.most_common(1)[0]
        if "missing" in top_reason.lower():
            suggestions.append(
                "Frequent missing-content failures detected. Consider stronger output constraints or structured generation."
            )
        if "unsafe" in top_reason.lower() or "policy" in top_reason.lower():
            suggestions.append(
                "Safety-related failures detected. Add stricter refusal logic or stronger validation before returning outputs."
            )
        if "format" in top_reason.lower() or "schema" in top_reason.lower():
            suggestions.append(
                "Formatting/schema failures detected. Enforce output validation before final return."
            )

    if not suggestions:
        suggestions.append(
            "No major systemic issue detected from current heuristics. Review individual failed runs for edge-case handling."
        )

    analysis = {
        "summary": {
            "total_runs": total_runs,
            "success_count": success_count,
            "failure_count": failure_count,
            "success_rate": round(success_rate, 4),
            "failure_rate": round(failure_rate, 4),
            "retry_count": retry_count,
            "retry_rate": round(retry_rate, 4),
            "average_steps": round(average_steps, 2),
        },
        "failure_reasons": [
            {"reason": reason, "count": count}
            for reason, count in failure_reason_counter.most_common()
        ],
        "path_patterns": [
            {"path": path, "count": count}
            for path, count in path_counter.most_common()
        ],
        "golden_path": {
            "path": golden_path,
            "deviation_count": golden_path_deviation_count,
            "deviation_rate": round(golden_path_deviation_rate, 4),
        },
        "suggested_improvements": suggestions,
    }

    return analysis


def format_console_report(analysis: dict[str, Any]) -> str:
    summary = analysis["summary"]
    failure_reasons = analysis["failure_reasons"]
    path_patterns = analysis["path_patterns"]
    golden_path = analysis["golden_path"]
    suggestions = analysis["suggested_improvements"]

    lines = []
    lines.append("=== PATH AUDIT REPORT ===")
    lines.append("")
    lines.append(f"Total runs: {summary['total_runs']}")
    lines.append(f"Success count: {summary['success_count']}")
    lines.append(f"Failure count: {summary['failure_count']}")
    lines.append(f"Success rate: {summary['success_rate'] * 100:.2f}%")
    lines.append(f"Failure rate: {summary['failure_rate'] * 100:.2f}%")
    lines.append(f"Retry count: {summary['retry_count']}")
    lines.append(f"Retry rate: {summary['retry_rate'] * 100:.2f}%")
    lines.append(f"Average steps per run: {summary['average_steps']}")
    lines.append("")

    lines.append("Top failure reasons:")
    if failure_reasons:
        for item in failure_reasons[:5]:
            lines.append(f"- {item['reason']} ({item['count']})")
    else:
        lines.append("- None")
    lines.append("")

    lines.append("Common execution paths:")
    for item in path_patterns[:5]:
        lines.append(f"- {item['path']} ({item['count']})")
    lines.append("")

    lines.append(f"Golden path: {golden_path['path']}")
    lines.append(f"Deviation from golden path: {golden_path['deviation_rate'] * 100:.2f}%")
    lines.append("")

    lines.append("Suggested improvements:")
    for suggestion in suggestions:
        lines.append(f"- {suggestion}")

    return "\n".join(lines)


def format_markdown_report(analysis: dict[str, Any]) -> str:
    summary = analysis["summary"]
    failure_reasons = analysis["failure_reasons"]
    path_patterns = analysis["path_patterns"]
    golden_path = analysis["golden_path"]
    suggestions = analysis["suggested_improvements"]

    lines = []
    lines.append("# PATH AUDIT Report")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- Total runs: {summary['total_runs']}")
    lines.append(f"- Success count: {summary['success_count']}")
    lines.append(f"- Failure count: {summary['failure_count']}")
    lines.append(f"- Success rate: {summary['success_rate'] * 100:.2f}%")
    lines.append(f"- Failure rate: {summary['failure_rate'] * 100:.2f}%")
    lines.append(f"- Retry count: {summary['retry_count']}")
    lines.append(f"- Retry rate: {summary['retry_rate'] * 100:.2f}%")
    lines.append(f"- Average steps per run: {summary['average_steps']}")
    lines.append("")

    lines.append("## Failure Reasons")
    if failure_reasons:
        for item in failure_reasons:
            lines.append(f"- {item['reason']}: {item['count']}")
    else:
        lines.append("- None")
    lines.append("")

    lines.append("## Common Execution Paths")
    for item in path_patterns:
        lines.append(f"- `{item['path']}`: {item['count']}")
    lines.append("")

    lines.append("## Golden Path")
    lines.append(f"- Path: `{golden_path['path']}`")
    lines.append(f"- Deviation count: {golden_path['deviation_count']}")
    lines.append(f"- Deviation rate: {golden_path['deviation_rate'] * 100:.2f}%")
    lines.append("")

    lines.append("## Suggested Improvements")
    for suggestion in suggestions:
        lines.append(f"- {suggestion}")
    lines.append("")

    return "\n".join(lines)


def save_outputs(output_dir: str, analysis: dict[str, Any], markdown_report: str) -> None:
    os.makedirs(output_dir, exist_ok=True)

    json_path = os.path.join(output_dir, "analysis_report.json")
    md_path = os.path.join(output_dir, "analysis_report.md")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(markdown_report)


def main() -> None:
    input_file = "sample_logs.json"
    output_dir = "output"

    runs = load_runs(input_file)
    analysis = analyze_runs(runs)

    console_report = format_console_report(analysis)
    markdown_report = format_markdown_report(analysis)

    print(console_report)
    save_outputs(output_dir, analysis, markdown_report)

    print("\nGenerated files:")
    print(f"- {os.path.join(output_dir, 'analysis_report.json')}")
    print(f"- {os.path.join(output_dir, 'analysis_report.md')}")


if __name__ == "__main__":
    main()