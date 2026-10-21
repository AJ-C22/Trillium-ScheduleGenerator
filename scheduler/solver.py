from __future__ import annotations

from collections import defaultdict

from ortools.sat.python import cp_model

from scheduler.models import OFF, ScheduleRequest, ScheduleResult
from scheduler.validation import preflight_errors, validate_assignments


def solve_schedule(request: ScheduleRequest) -> ScheduleResult:
    diagnostics = preflight_errors(request)
    if diagnostics:
        return ScheduleResult(
            status="INVALID_INPUT",
            assignments={},
            objective_value=None,
            diagnostics=tuple(diagnostics),
        )

    model = cp_model.CpModel()
    assign: dict[tuple[int, int, str], cp_model.IntVar] = {}
    all_roles = (*request.roles, OFF)

    for staff_index, member in enumerate(request.staff):
        for period_index, period in enumerate(request.periods):
            period_vars = []
            for role in all_roles:
                variable = model.new_bool_var(
                    f"assign_s{staff_index}_p{period_index}_{role}"
                )
                assign[staff_index, period_index, role] = variable
                period_vars.append(variable)
            model.add_exactly_one(period_vars)

            if period.id in member.unavailable:
                model.add(assign[staff_index, period_index, OFF] == 1)
            fixed = member.fixed_assignments.get(period.id)
            if fixed is not None:
                model.add(assign[staff_index, period_index, fixed] == 1)
            for role in request.roles:
                if role not in member.eligible_roles:
                    model.add(assign[staff_index, period_index, role] == 0)
            for role in all_roles:
                if role in member.forbidden_assignments.get(period.id, frozenset()):
                    model.add(assign[staff_index, period_index, role] == 0)

    for period_index, period in enumerate(request.periods):
        for role in request.roles:
            model.add(
                sum(
                    assign[staff_index, period_index, role]
                    for staff_index in range(len(request.staff))
                )
                == period.requirements.get(role, 0)
            )

    workload_counts: dict[tuple[int, str], cp_model.IntVar] = {}
    objective_terms: list[cp_model.LinearExpr] = []
    number_of_periods = len(request.periods)

    for staff_index, member in enumerate(request.staff):
        for role in all_roles:
            count = model.new_int_var(
                0, number_of_periods, f"count_s{staff_index}_{role}"
            )
            model.add(
                count
                == sum(
                    assign[staff_index, period_index, role]
                    for period_index in range(number_of_periods)
                )
            )
            workload_counts[staff_index, role] = count

        for target_key, target in member.workload_targets.items():
            if target_key in request.role_groups:
                count = model.new_int_var(
                    0, number_of_periods, f"count_s{staff_index}_{target_key}"
                )
                model.add(
                    count
                    == sum(
                        workload_counts[staff_index, role]
                        for role in request.role_groups[target_key]
                    )
                )
            else:
                count = workload_counts[staff_index, target_key]
            maximum = number_of_periods if target.maximum is None else target.maximum
            model.add(count >= target.minimum)
            model.add(count <= maximum)
            if target.preferred is not None and target.weight:
                deviation = model.new_int_var(
                    0, number_of_periods, f"deviation_s{staff_index}_{target_key}"
                )
                model.add_abs_equality(deviation, count - target.preferred)
                objective_terms.append(target.weight * deviation)

        for preference_index, preference in enumerate(member.preferences):
            period_index = next(
                index
                for index, period in enumerate(request.periods)
                if period.id == preference.period
            )
            variable = assign[staff_index, period_index, preference.role]
            if preference.kind == "prefer":
                missed = model.new_bool_var(
                    f"missed_preference_s{staff_index}_{preference_index}"
                )
                model.add(missed + variable == 1)
                objective_terms.append(preference.weight * missed)
            else:
                objective_terms.append(preference.weight * variable)

        for role in request.roles:
            limit = member.max_consecutive.get(
                role, request.rules.default_max_consecutive.get(role)
            )
            if limit is not None:
                for start in range(number_of_periods - limit):
                    model.add(
                        sum(
                            assign[staff_index, period_index, role]
                            for period_index in range(start, start + limit + 1)
                        )
                        <= limit
                    )

            consecutive_weight = request.rules.consecutive_role_weights.get(
                role, request.rules.consecutive_assignment_weight
            )
            if consecutive_weight:
                for period_index in range(1, number_of_periods):
                    consecutive = model.new_bool_var(
                        f"consecutive_s{staff_index}_p{period_index}_{role}"
                    )
                    previous = assign[staff_index, period_index - 1, role]
                    current = assign[staff_index, period_index, role]
                    model.add(consecutive <= previous)
                    model.add(consecutive <= current)
                    model.add(consecutive >= previous + current - 1)
                    objective_terms.append(consecutive_weight * consecutive)

        forced_off = [
            period.id in member.unavailable
            or member.fixed_assignments.get(period.id) == OFF
            for period in request.periods
        ]
        if request.rules.consecutive_off_weight:
            for period_index in range(1, number_of_periods):
                if forced_off[period_index - 1] and forced_off[period_index]:
                    continue
                consecutive_off = model.new_bool_var(
                    f"consecutive_off_s{staff_index}_p{period_index}"
                )
                previous = assign[staff_index, period_index - 1, OFF]
                current = assign[staff_index, period_index, OFF]
                model.add(consecutive_off <= previous)
                model.add(consecutive_off <= current)
                model.add(consecutive_off >= previous + current - 1)
                objective_terms.append(
                    request.rules.consecutive_off_weight * consecutive_off
                )

        if request.rules.long_run_weight:
            for role in all_roles:
                for start in range(number_of_periods - 2):
                    if role == OFF and all(forced_off[start : start + 3]):
                        continue
                    long_run = model.new_bool_var(
                        f"long_run_s{staff_index}_p{start}_{role}"
                    )
                    run_variables = [
                        assign[staff_index, period_index, role]
                        for period_index in range(start, start + 3)
                    ]
                    for variable in run_variables:
                        model.add(long_run <= variable)
                    model.add(long_run >= sum(run_variables) - 2)
                    objective_terms.append(request.rules.long_run_weight * long_run)

    model.minimize(sum(objective_terms) if objective_terms else 0)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = request.rules.time_limit_seconds
    solver.parameters.num_search_workers = 8
    solver.parameters.random_seed = request.rules.random_seed
    status_code = solver.solve(model)
    status = solver.status_name(status_code)

    if status not in {"OPTIMAL", "FEASIBLE"}:
        return ScheduleResult(
            status=status,
            assignments={},
            objective_value=None,
            diagnostics=(
                "No schedule satisfies every hard constraint.",
                "Review fixed assignments, eligibility, availability, workload bounds, "
                "and consecutive-assignment limits.",
            ),
        )

    assignments: dict[str, dict[str, str]] = defaultdict(dict)
    for period_index, period in enumerate(request.periods):
        for staff_index, member in enumerate(request.staff):
            assigned_role = next(
                role
                for role in all_roles
                if solver.value(assign[staff_index, period_index, role])
            )
            assignments[period.id][member.id] = assigned_role

    validation_errors = validate_assignments(request, assignments)
    return ScheduleResult(
        status=status,
        assignments=dict(assignments),
        objective_value=solver.objective_value,
        validation_errors=tuple(validation_errors),
    )
