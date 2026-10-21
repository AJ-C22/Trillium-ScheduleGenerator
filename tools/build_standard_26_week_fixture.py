#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


def exact_targets(index: int) -> dict[str, int]:
    return {
        "CTU": 2 if index <= 21 else 1,
        "Inpatient": 6 if index == 1 else 5,
        "Clinic": 2 if index <= 21 else 1,
        "ER": 4 if index <= 11 else 3,
        "Consult": 1 if index <= 26 else 0,
    }


def build_fixture() -> dict[str, object]:
    periods = [
        {
            "id": f"W{week:02d}",
            "label": f"Week {week:02d}",
            "requirements": {
                "CTU": 2,
                "Inpatient": 6,
                "Clinic": 2,
                "ER": 4,
                "Consult": 1,
            },
        }
        for week in range(1, 27)
    ]

    staff = []
    for index in range(1, 32):
        targets = exact_targets(index)
        targets["OFF"] = 26 - sum(targets.values())
        first_off = ((index - 1) * 3) % 26 + 1
        second_off = ((index - 1) * 3 + 8) % 26 + 1
        staff.append(
            {
                "id": f"doctor-{index:02d}",
                "name": f"Doctor {index:02d}",
                "eligible_roles": ["CTU", "Inpatient", "Clinic", "ER", "Consult"],
                "unavailable": [f"W{first_off:02d}", f"W{second_off:02d}"],
                "workload_targets": targets,
            }
        )

    return {
        "name": "Standard 26-week hospital schedule",
        "roles": ["CTU", "Inpatient", "Clinic", "ER", "Consult"],
        "periods": periods,
        "staff": staff,
        "rules": {
            "consecutive_assignment_weight": 4,
            "consecutive_off_weight": 6,
            "long_run_weight": 12,
            "time_limit_seconds": 120,
            "random_seed": 1,
        },
    }


if __name__ == "__main__":
    destination = Path("examples/standard_26_week.json")
    destination.write_text(
        json.dumps(build_fixture(), indent=2) + "\n",
        encoding="utf-8",
    )
    print(destination)
