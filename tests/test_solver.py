import csv

from scheduler.cli import write_schedule_csv
from scheduler.models import ScheduleRequest
from scheduler.solver import solve_schedule


def feasible_request() -> ScheduleRequest:
    return ScheduleRequest.from_dict(
        {
            "name": "Two-week test",
            "roles": ["Ward", "Clinic"],
            "periods": [
                {"id": "W1", "requirements": {"Ward": 1, "Clinic": 1}},
                {"id": "W2", "requirements": {"Ward": 1, "Clinic": 1}},
            ],
            "staff": [
                {
                    "id": "a",
                    "eligible_roles": ["Ward"],
                    "workload_targets": {"Ward": 1},
                },
                {
                    "id": "b",
                    "eligible_roles": ["Clinic"],
                    "workload_targets": {"Clinic": 2},
                },
                {
                    "id": "c",
                    "eligible_roles": ["Ward", "Clinic"],
                    "unavailable": ["W1"],
                    "fixed_assignments": {"W2": "Ward"},
                    "workload_targets": {"Ward": 1},
                },
            ],
        }
    )


def test_solver_satisfies_hard_constraints_exactly() -> None:
    request = feasible_request()
    result = solve_schedule(request)

    assert result.is_success
    assert result.validation_errors == ()
    assert result.assignments["W1"] == {"a": "Ward", "b": "Clinic", "c": "OFF"}
    assert result.assignments["W2"] == {"a": "OFF", "b": "Clinic", "c": "Ward"}


def test_preflight_reports_obvious_staffing_shortage() -> None:
    request = ScheduleRequest.from_dict(
        {
            "roles": ["CTU"],
            "periods": [{"id": "W1", "requirements": {"CTU": 2}}],
            "staff": [{"id": "only-doctor", "eligible_roles": ["CTU"]}],
        }
    )

    result = solve_schedule(request)

    assert result.status == "INVALID_INPUT"
    assert any("only 1 staff exist" in message for message in result.diagnostics)


def test_infeasible_model_never_returns_a_partial_schedule() -> None:
    request = ScheduleRequest.from_dict(
        {
            "roles": ["Ward"],
            "periods": [
                {"id": "W1", "requirements": {"Ward": 1}},
                {"id": "W2", "requirements": {"Ward": 1}},
            ],
            "staff": [
                {
                    "id": "doctor",
                    "eligible_roles": ["Ward"],
                    "max_consecutive": {"Ward": 1},
                }
            ],
        }
    )

    result = solve_schedule(request)

    assert result.status == "INFEASIBLE"
    assert result.assignments == {}
    assert not result.is_success


def test_csv_has_staff_on_left_and_weeks_across_top(tmp_path) -> None:
    request = feasible_request()
    result = solve_schedule(request)
    output = tmp_path / "schedule.csv"

    write_schedule_csv(request, result, output)

    with output.open(newline="", encoding="utf-8") as file:
        rows = list(csv.reader(file))

    assert rows == [
        ["Staff member", "W1", "W2"],
        ["a", "Ward", "X"],
        ["b", "Clinic", "Clinic"],
        ["c", "X", "Ward"],
    ]
