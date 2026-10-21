from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import openpyxl

from scheduler.models import (
    OFF,
    Period,
    ScheduleRequest,
    ScheduleRules,
    StaffMember,
    WorkloadTarget,
)

CORE_FIRST_COLUMN = 4
CORE_LAST_COLUMN = 34
EXTERNAL_COLUMN = 35
FIRST_PERIOD_ROW = 2
LAST_PERIOD_ROW = 27

ROLES = ("CTU", "Inpatient", "Clinic", "ER", "Consult", "Holiday Coverage")
STAT_ROWS = {
    "CTU": 37,
    "Inpatient": 38,
    "Clinic": 39,
    "ER": 40,
    "Consult": 41,
    "Holiday Coverage": 42,
}


@dataclass(frozen=True)
class Imported2026BBenchmark:
    request: ScheduleRequest
    baseline_assignments: dict[str, dict[str, str]]
    external_coverage: dict[str, dict[str, str]]
    interpreted_notes: tuple[str, ...]
    unresolved_cells: tuple[str, ...]


def canonical_assignment(value: Any) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return "Holiday Coverage"

    text = str(value).strip().lower()
    if text.startswith("x") or text == "mh":
        return OFF
    if "ctu" in text:
        return "CTU"
    if "inpt" in text or "in-patient" in text:
        return "Inpatient"
    if text.startswith("clinic"):
        return "Clinic"
    if text.startswith("er"):
        return "ER"
    if text.startswith("consult"):
        return "Consult"
    return None


def _staff_id(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _number(value: Any) -> int:
    if value in (None, ""):
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    match = re.match(r"\s*(\d+)", str(value))
    return int(match.group(1)) if match else 0


def import_2026b_benchmark(
    template_path: str | Path,
    completed_path: str | Path,
) -> Imported2026BBenchmark:
    template = openpyxl.load_workbook(template_path, data_only=False).active
    completed = openpyxl.load_workbook(completed_path, data_only=False).active

    doctors = [
        str(template.cell(1, column).value).strip()
        for column in range(CORE_FIRST_COLUMN, CORE_LAST_COLUMN + 1)
    ]
    period_ids = [f"W{index:02d}" for index in range(1, 27)]
    periods: list[Period] = []
    baseline: dict[str, dict[str, str]] = {}
    external_coverage: dict[str, dict[str, str]] = {}
    unresolved: list[str] = []
    interpreted: list[str] = []

    for period_index, row in enumerate(
        range(FIRST_PERIOD_ROW, LAST_PERIOD_ROW + 1)
    ):
        period_id = period_ids[period_index]
        assignments: dict[str, str] = {}
        coverage: Counter[str] = Counter()

        for doctor, column in zip(
            doctors, range(CORE_FIRST_COLUMN, CORE_LAST_COLUMN + 1)
        ):
            value = completed.cell(row, column).value
            assignment = canonical_assignment(value)
            if assignment is None:
                unresolved.append(
                    f"completed:{completed.cell(row, column).coordinate}={value!r}"
                )
                continue
            assignments[_staff_id(doctor)] = assignment
            if assignment != OFF:
                coverage[assignment] += 1

        baseline[period_id] = assignments
        periods.append(
            Period(
                id=period_id,
                label=str(template.cell(row, 1).value).strip(),
                requirements={role: coverage[role] for role in ROLES},
            )
        )

        external_value = completed.cell(row, EXTERNAL_COLUMN).value
        external_role = canonical_assignment(external_value)
        if external_value not in (None, ""):
            external_coverage[period_id] = {
                "description": str(external_value),
                "role": external_role or "Unclassified",
            }

    staff: list[StaffMember] = []
    for doctor, column in zip(
        doctors, range(CORE_FIRST_COLUMN, CORE_LAST_COLUMN + 1)
    ):
        staff_id = _staff_id(doctor)
        unavailable: set[str] = set()
        fixed: dict[str, str] = {}
        forbidden: dict[str, frozenset[str]] = {}

        for period_index, row in enumerate(
            range(FIRST_PERIOD_ROW, LAST_PERIOD_ROW + 1)
        ):
            period_id = period_ids[period_index]
            value = template.cell(row, column).value
            nonholiday_number = (
                isinstance(value, (int, float)) and row not in {14, 15}
            )
            assignment = None if nonholiday_number else canonical_assignment(value)
            if assignment == OFF:
                unavailable.add(period_id)
            elif assignment is not None:
                fixed[period_id] = assignment
            elif value not in (None, ""):
                text = str(value).strip()
                lower = text.lower()
                if lower in {"mrp", "on"} or nonholiday_number:
                    forbidden[period_id] = frozenset({OFF})
                    interpreted.append(
                        f"{template.cell(row, column).coordinate}: "
                        f"{text!r} interpreted as must work"
                    )
                else:
                    unresolved.append(
                        f"template:{template.cell(row, column).coordinate}={value!r}"
                    )

        eligible = set(ROLES)
        if str(template.cell(36, column).value).strip().lower() == "no ctu":
            eligible.discard("CTU")

        targets = {
            role: WorkloadTarget(
                minimum=0,
                maximum=26,
                preferred=_number(template.cell(row, column).value),
                weight=10,
            )
            for role, row in STAT_ROWS.items()
        }
        targets[OFF] = WorkloadTarget(
            minimum=0,
            maximum=26,
            preferred=_number(template.cell(47, column).value),
            weight=4,
        )

        staff.append(
            StaffMember(
                id=staff_id,
                name=doctor,
                eligible_roles=frozenset(eligible),
                unavailable=frozenset(unavailable),
                fixed_assignments=fixed,
                forbidden_assignments=forbidden,
                workload_targets=targets,
            )
        )

    request = ScheduleRequest(
        name="2026B Trillium benchmark",
        roles=ROLES,
        role_groups={},
        periods=tuple(periods),
        staff=tuple(staff),
        rules=ScheduleRules(
            consecutive_assignment_weight=3,
            consecutive_role_weights={"CTU": 0},
            consecutive_off_weight=5,
            long_run_weight=8,
            time_limit_seconds=120,
            random_seed=1,
        ),
    )
    return Imported2026BBenchmark(
        request=request,
        baseline_assignments=baseline,
        external_coverage=external_coverage,
        interpreted_notes=tuple(interpreted),
        unresolved_cells=tuple(unresolved),
    )


def request_as_dict(request: ScheduleRequest) -> dict[str, Any]:
    return {
        "name": request.name,
        "roles": list(request.roles),
        "role_groups": {
            group: list(roles) for group, roles in request.role_groups.items()
        },
        "periods": [
            {
                "id": period.id,
                "label": period.label,
                "requirements": period.requirements,
            }
            for period in request.periods
        ],
        "staff": [
            {
                "id": member.id,
                "name": member.name,
                "eligible_roles": sorted(member.eligible_roles),
                "unavailable": sorted(member.unavailable),
                "fixed_assignments": member.fixed_assignments,
                "forbidden_assignments": {
                    period: sorted(roles)
                    for period, roles in member.forbidden_assignments.items()
                },
                "workload_targets": {
                    role: {
                        "min": target.minimum,
                        "max": target.maximum,
                        "preferred": target.preferred,
                        "weight": target.weight,
                    }
                    for role, target in member.workload_targets.items()
                },
            }
            for member in request.staff
        ],
        "rules": {
            "default_max_consecutive": request.rules.default_max_consecutive,
            "consecutive_assignment_weight": (
                request.rules.consecutive_assignment_weight
            ),
            "consecutive_role_weights": request.rules.consecutive_role_weights,
            "consecutive_off_weight": request.rules.consecutive_off_weight,
            "long_run_weight": request.rules.long_run_weight,
            "time_limit_seconds": request.rules.time_limit_seconds,
            "random_seed": request.rules.random_seed,
        },
    }
