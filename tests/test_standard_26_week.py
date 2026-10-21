from collections import Counter
from pathlib import Path

from scheduler.cli import load_request
from scheduler.solver import solve_schedule


def test_standard_26_week_schedule_solves_at_realistic_scale() -> None:
    request = load_request(Path("examples/standard_26_week.json"))

    assert len(request.periods) == 26
    assert len(request.staff) == 31
    assert sum(request.periods[0].requirements.values()) == 15

    result = solve_schedule(request)

    assert result.is_success
    assert result.validation_errors == ()

    for period in request.periods:
        counts = Counter(result.assignments[period.id].values())
        assert counts["CTU"] == 2
        assert counts["Inpatient"] == 6
        assert counts["Clinic"] == 2
        assert counts["ER"] == 4
        assert counts["Consult"] == 1

    for member in request.staff:
        counts = Counter(
            result.assignments[period.id][member.id] for period in request.periods
        )
        for role, target in member.workload_targets.items():
            assert counts[role] == target.preferred
        for period_id in member.unavailable:
            assert result.assignments[period_id][member.id] == "OFF"
