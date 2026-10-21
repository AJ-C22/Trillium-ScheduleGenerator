from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Sequence

from scheduler.models import OFF, ScheduleRequest, ScheduleResult
from scheduler.solver import solve_schedule


def load_request(path: Path) -> ScheduleRequest:
    if path.suffix.lower() == ".json":
        return ScheduleRequest.from_dict(json.loads(path.read_text(encoding="utf-8")))
    raise ValueError("Input must be a structured .json file.")


def write_schedule_csv(
    request: ScheduleRequest, result: ScheduleResult, path: Path
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Staff member", *(period.label for period in request.periods)])
        for member in request.staff:
            writer.writerow(
                [
                    member.name,
                    *(
                        "X"
                        if result.assignments[period.id][member.id] == OFF
                        else result.assignments[period.id][member.id]
                        for period in request.periods
                    ),
                ]
            )


def build_report(request: ScheduleRequest, result: ScheduleResult) -> dict[str, object]:
    workloads: dict[str, dict[str, int]] = {}
    quality = {
        "consecutive_same_role_pairs": 0,
        "consecutive_off_pairs": 0,
        "three_period_runs": 0,
        "preferences_satisfied": 0,
        "preferences_total": 0,
    }
    if result.assignments:
        for member in request.staff:
            sequence = [
                result.assignments[period.id][member.id] for period in request.periods
            ]
            workloads[member.id] = dict(
                Counter(sequence)
            )
            quality["consecutive_same_role_pairs"] += sum(
                previous == current and current != OFF
                for previous, current in zip(sequence, sequence[1:])
            )
            quality["consecutive_off_pairs"] += sum(
                previous == current == OFF
                for previous, current in zip(sequence, sequence[1:])
            )
            quality["three_period_runs"] += sum(
                first == second == third
                for first, second, third in zip(sequence, sequence[1:], sequence[2:])
            )
            for preference in member.preferences:
                assigned = result.assignments[preference.period][member.id]
                quality["preferences_total"] += 1
                quality["preferences_satisfied"] += (
                    assigned == preference.role
                    if preference.kind == "prefer"
                    else assigned != preference.role
                )
    return {
        "schedule": request.name,
        "status": result.status,
        "success": result.is_success,
        "objective_value": result.objective_value,
        "validation_errors": list(result.validation_errors),
        "diagnostics": list(result.diagnostics),
        "quality": quality,
        "workloads": workloads,
    }


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a feasibility-first hospital schedule."
    )
    parser.add_argument("input", type=Path, help="Schedule request (.json)")
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("output/schedule.csv"),
        help="Generated schedule CSV",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("output/report.json"),
        help="Machine-readable validation report",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = create_parser().parse_args(argv)
    try:
        request = load_request(args.input)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        print(f"Input error: {error}")
        return 2

    result = solve_schedule(request)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(build_report(request, result), indent=2) + "\n",
        encoding="utf-8",
    )

    if not result.is_success:
        print(f"Schedule not generated: {result.status}")
        for message in (*result.diagnostics, *result.validation_errors):
            print(f"- {message}")
        print(f"Report: {args.report}")
        return 2

    write_schedule_csv(request, result, args.output)
    print(f"Schedule generated: {result.status}")
    print(f"Objective value: {result.objective_value}")
    print(f"Schedule: {args.output}")
    print(f"Report: {args.report}")
    return 0
