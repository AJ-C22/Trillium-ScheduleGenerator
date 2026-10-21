#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from scheduler.cli import build_report, write_schedule_csv
from scheduler.importers.trillium_2026b import (
    import_2026b_benchmark,
    request_as_dict,
)
from scheduler.models import ScheduleResult
from scheduler.solver import solve_schedule

TEMPLATE = Path("Copy of 2026B Call Schedule Oct 2026 - Mar 2027 - TEMPLATE FINAL.xlsx")
COMPLETED = Path(
    "Copy of 2026B Call Schedule Oct 2026 - Mar 2027 - COMPLETED DRAFT with STATS.xlsx"
)


def main() -> int:
    imported = import_2026b_benchmark(TEMPLATE, COMPLETED)
    Path("examples/2026b_imported.json").write_text(
        json.dumps(request_as_dict(imported.request), indent=2) + "\n",
        encoding="utf-8",
    )

    result = solve_schedule(imported.request)
    report = build_report(imported.request, result)
    Path("output").mkdir(exist_ok=True)
    Path("output/2026b-report.json").write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    if not result.is_success:
        print(result.status)
        for message in (*result.diagnostics, *result.validation_errors):
            print(message)
        return 2

    write_schedule_csv(imported.request, result, Path("output/2026b-schedule.csv"))
    baseline_result = ScheduleResult(
        status="BASELINE",
        assignments=imported.baseline_assignments,
        objective_value=None,
    )
    baseline_report = build_report(imported.request, baseline_result)

    total_cells = len(imported.request.periods) * len(imported.request.staff)
    exact_matches = sum(
        result.assignments[period.id][member.id]
        == imported.baseline_assignments[period.id][member.id]
        for period in imported.request.periods
        for member in imported.request.staff
    )
    comparison = {
        "generated_status": result.status,
        "generated_objective": result.objective_value,
        "cells_compared": total_cells,
        "exact_category_matches": exact_matches,
        "exact_category_match_percent": round(100 * exact_matches / total_cells, 2),
        "generated_quality": report["quality"],
        "completed_draft_quality": baseline_report["quality"],
        "external_coverage": imported.external_coverage,
        "interpreted_notes": list(imported.interpreted_notes),
        "unresolved_cells": list(imported.unresolved_cells),
        "important_scope_note": (
            "Roles are normalized to CTU, Inpatient, Clinic, ER, Consult, "
            "Holiday Coverage, and OFF because several completed cells do not "
            "identify a detailed service line."
        ),
    }
    Path("output/2026b-comparison.json").write_text(
        json.dumps(comparison, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(comparison, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
