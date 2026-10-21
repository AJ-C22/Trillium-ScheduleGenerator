from collections import Counter
from pathlib import Path

from scheduler.importers.trillium_2026b import import_2026b_benchmark
from scheduler.solver import solve_schedule
from scheduler.validation import (
    preflight_errors,
    validate_assignments,
)

TEMPLATE = Path("Copy of 2026B Call Schedule Oct 2026 - Mar 2027 - TEMPLATE FINAL.xlsx")
COMPLETED = Path(
    "Copy of 2026B Call Schedule Oct 2026 - Mar 2027 - COMPLETED DRAFT with STATS.xlsx"
)


def test_2026b_workbooks_normalize_without_unresolved_cells() -> None:
    imported = import_2026b_benchmark(TEMPLATE, COMPLETED)

    assert len(imported.request.periods) == 26
    assert len(imported.request.staff) == 31
    assert imported.unresolved_cells == ()
    assert len(imported.external_coverage) == 12
    assert preflight_errors(imported.request) == []
    assert validate_assignments(
        imported.request, imported.baseline_assignments
    ) == []


def test_2026b_schedule_satisfies_real_workbook_constraints() -> None:
    imported = import_2026b_benchmark(TEMPLATE, COMPLETED)

    result = solve_schedule(imported.request)

    assert result.is_success
    assert result.validation_errors == ()
    for period in imported.request.periods:
        actual = Counter(result.assignments[period.id].values())
        for role, required in period.requirements.items():
            assert actual[role] == required
    for member in imported.request.staff:
        for period_id in member.unavailable:
            assert result.assignments[period_id][member.id] == "OFF"
        for period_id, role in member.fixed_assignments.items():
            assert result.assignments[period_id][member.id] == role
