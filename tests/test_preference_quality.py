from collections import Counter
from pathlib import Path

from scheduler.cli import load_request
from scheduler.models import OFF, ScheduleRequest
from scheduler.solver import solve_schedule


def test_preference_example_is_valid_and_well_spaced() -> None:
    request = load_request(Path("examples/preference_spacing.json"))

    result = solve_schedule(request)

    assert result.is_success
    assert result.validation_errors == ()
    assert result.assignments["W1"]["doctor-a"] == OFF
    assert result.assignments["W2"]["doctor-a"] != OFF
    assert result.assignments["W1"]["doctor-b"] == "ER"
    assert result.assignments["W2"]["doctor-c"] != "Clinic"
    assert result.assignments["W4"]["doctor-d"] == "Ward"

    for period in request.periods:
        counts = Counter(result.assignments[period.id].values())
        assert counts["ER"] == 1
        assert counts["Ward"] == 1
        assert counts["Clinic"] == 1

    for member in request.staff:
        assignments = [
            result.assignments[period.id][member.id] for period in request.periods
        ]
        assert all(
            current != previous
            for previous, current in zip(assignments, assignments[1:])
        )


def test_preset_leave_run_is_not_treated_as_an_error() -> None:
    request = ScheduleRequest.from_dict(
        {
            "roles": ["Ward"],
            "periods": [
                {"id": "W1", "requirements": {"Ward": 0}},
                {"id": "W2", "requirements": {"Ward": 0}},
                {"id": "W3", "requirements": {"Ward": 0}},
            ],
            "staff": [
                {
                    "id": "doctor",
                    "eligible_roles": ["Ward"],
                    "unavailable": ["W1", "W2", "W3"],
                }
            ],
            "rules": {
                "consecutive_off_weight": 20,
                "long_run_weight": 20,
            },
        }
    )

    result = solve_schedule(request)

    assert result.is_success
    assert result.objective_value == 0
