from __future__ import annotations

from collections import Counter

from scheduler.models import OFF, ScheduleRequest


def preflight_errors(request: ScheduleRequest) -> list[str]:
    errors: list[str] = []
    role_set = set(request.roles)
    group_set = set(request.role_groups)
    period_ids = [period.id for period in request.periods]
    staff_ids = [member.id for member in request.staff]
    period_set = set(period_ids)

    if not request.roles:
        errors.append("At least one role is required.")
    if OFF in role_set:
        errors.append(f"{OFF} is reserved; do not include it in roles.")
    if len(role_set) != len(request.roles):
        errors.append("Role IDs must be unique.")
    if role_set & group_set:
        errors.append("Role and role-group IDs must not overlap.")
    for group, roles in request.role_groups.items():
        unknown = set(roles) - role_set
        if unknown:
            errors.append(f"Role group {group}: unknown roles {sorted(unknown)}.")
        if not roles:
            errors.append(f"Role group {group} must contain at least one role.")
    if len(set(period_ids)) != len(period_ids):
        errors.append("Period IDs must be unique.")
    if len(set(staff_ids)) != len(staff_ids):
        errors.append("Staff IDs must be unique.")
    if not request.periods:
        errors.append("At least one period is required.")
    if not request.staff:
        errors.append("At least one staff member is required.")
    unknown_weight_roles = set(request.rules.consecutive_role_weights) - role_set
    if unknown_weight_roles:
        errors.append(
            f"Unknown consecutive-role weights {sorted(unknown_weight_roles)}."
        )
    if any(
        weight < 0
        for weight in (
            request.rules.consecutive_assignment_weight,
            request.rules.consecutive_off_weight,
            request.rules.long_run_weight,
            *request.rules.consecutive_role_weights.values(),
        )
    ):
        errors.append("Schedule-quality weights cannot be negative.")

    for period in request.periods:
        unknown = set(period.requirements) - role_set
        if unknown:
            errors.append(f"{period.id}: unknown required roles {sorted(unknown)}.")
        if any(count < 0 for count in period.requirements.values()):
            errors.append(f"{period.id}: coverage counts cannot be negative.")
        required = sum(period.requirements.values())
        if required > len(request.staff):
            errors.append(
                f"{period.id}: requires {required} assignments but only "
                f"{len(request.staff)} staff exist."
            )

    for member in request.staff:
        unknown_eligible = set(member.eligible_roles) - role_set
        if unknown_eligible:
            errors.append(f"{member.id}: unknown eligible roles {sorted(unknown_eligible)}.")
        unknown_periods = (
            set(member.unavailable)
            | set(member.fixed_assignments)
            | set(member.forbidden_assignments)
            | {preference.period for preference in member.preferences}
        ) - period_set
        if unknown_periods:
            errors.append(f"{member.id}: unknown periods {sorted(unknown_periods)}.")
        unknown_roles = (
            set(member.fixed_assignments.values())
            | set(member.max_consecutive)
            | {preference.role for preference in member.preferences}
        ) - role_set - {OFF}
        if unknown_roles:
            errors.append(f"{member.id}: unknown roles {sorted(unknown_roles)}.")
        unknown_target_keys = set(member.workload_targets) - role_set - group_set - {OFF}
        if unknown_target_keys:
            errors.append(
                f"{member.id}: unknown workload roles/groups {sorted(unknown_target_keys)}."
            )
        forbidden_roles = {
            role
            for roles in member.forbidden_assignments.values()
            for role in roles
        } - role_set - {OFF}
        if forbidden_roles:
            errors.append(
                f"{member.id}: unknown forbidden roles {sorted(forbidden_roles)}."
            )

        for period, role in member.fixed_assignments.items():
            if period in member.unavailable and role != OFF:
                errors.append(
                    f"{member.id}/{period}: fixed to {role} but also unavailable."
                )
            if role != OFF and role not in member.eligible_roles:
                errors.append(
                    f"{member.id}/{period}: fixed to ineligible role {role}."
                )
            if role in member.forbidden_assignments.get(period, frozenset()):
                errors.append(
                    f"{member.id}/{period}: fixed to forbidden role {role}."
                )

        for role, target in member.workload_targets.items():
            maximum = len(request.periods) if target.maximum is None else target.maximum
            if target.minimum < 0 or maximum < target.minimum:
                errors.append(f"{member.id}/{role}: invalid workload bounds.")
            if target.preferred is not None and not target.minimum <= target.preferred <= maximum:
                errors.append(
                    f"{member.id}/{role}: preferred workload must be inside min/max."
                )
            eligible_for_target = (
                role == OFF
                or role in member.eligible_roles
                or (
                    role in request.role_groups
                    and bool(set(request.role_groups[role]) & set(member.eligible_roles))
                )
            )
            if not eligible_for_target and target.minimum > 0:
                errors.append(
                    f"{member.id}/{role}: positive workload minimum for an ineligible role."
                )

        minimum_total = sum(target.minimum for target in member.workload_targets.values())
        if minimum_total > len(request.periods):
            errors.append(
                f"{member.id}: workload minimums total {minimum_total}, exceeding "
                f"{len(request.periods)} periods."
            )

        for preference in member.preferences:
            if preference.kind not in {"prefer", "avoid"}:
                errors.append(
                    f"{member.id}/{preference.period}/{preference.role}: "
                    f"preference kind must be 'prefer' or 'avoid'."
                )
            if preference.weight < 0:
                errors.append(
                    f"{member.id}/{preference.period}/{preference.role}: "
                    "preference weight cannot be negative."
                )

    for period in request.periods:
        fixed_counts = Counter(
            member.fixed_assignments.get(period.id)
            for member in request.staff
            if member.fixed_assignments.get(period.id) not in {None, OFF}
        )
        for role in request.roles:
            requirement = period.requirements.get(role, 0)
            if fixed_counts[role] > requirement:
                errors.append(
                    f"{period.id}/{role}: {fixed_counts[role]} fixed assignments exceed "
                    f"required coverage {requirement}."
                )
            candidates = sum(
                1
                for member in request.staff
                if role in member.eligible_roles
                and period.id not in member.unavailable
                and member.fixed_assignments.get(period.id) in {None, role}
                and role not in member.forbidden_assignments.get(period.id, frozenset())
            )
            if candidates < requirement:
                errors.append(
                    f"{period.id}/{role}: needs {requirement}, but only "
                    f"{candidates} eligible and available staff can cover it."
                )

    total_by_role = {
        role: sum(period.requirements.get(role, 0) for period in request.periods)
        for role in request.roles
    }
    for role, total in total_by_role.items():
        minimum = sum(
            member.workload_targets.get(role).minimum
            for member in request.staff
            if role in member.workload_targets
        )
        maximum = sum(
            (
                member.workload_targets[role].maximum
                if member.workload_targets[role].maximum is not None
                else len(request.periods)
            )
            if role in member.workload_targets
            else len(request.periods)
            for member in request.staff
            if role in member.eligible_roles
        )
        if minimum > total:
            errors.append(
                f"{role}: staff workload minimums total {minimum}, but only {total} slots exist."
            )
        if maximum < total:
            errors.append(
                f"{role}: staff workload maximums total {maximum}, but {total} slots exist."
            )

    for group, roles in request.role_groups.items():
        total = sum(
            sum(period.requirements.get(role, 0) for role in roles)
            for period in request.periods
        )
        targeted = [
            member.workload_targets[group]
            for member in request.staff
            if group in member.workload_targets
        ]
        minimum = sum(target.minimum for target in targeted)
        maximum = sum(
            len(request.periods) if target.maximum is None else target.maximum
            for target in targeted
        ) + sum(
            len(request.periods)
            for member in request.staff
            if group not in member.workload_targets
            and set(roles) & set(member.eligible_roles)
        )
        if minimum > total:
            errors.append(
                f"{group}: staff workload minimums total {minimum}, "
                f"but only {total} grouped slots exist."
            )
        if maximum < total:
            errors.append(
                f"{group}: staff workload maximums total {maximum}, "
                f"but {total} grouped slots exist."
            )

    return errors


def validate_assignments(
    request: ScheduleRequest, assignments: dict[str, dict[str, str]]
) -> list[str]:
    errors: list[str] = []
    valid_roles = set(request.roles) | {OFF}
    period_by_id = {period.id: period for period in request.periods}

    for period in request.periods:
        assigned = assignments.get(period.id, {})
        missing = [member.id for member in request.staff if member.id not in assigned]
        if missing:
            errors.append(f"{period.id}: missing assignments for {missing}.")
            continue
        counts = Counter(assigned.values())
        for member in request.staff:
            role = assigned[member.id]
            if role not in valid_roles:
                errors.append(f"{member.id}/{period.id}: unknown assigned role {role}.")
            if period.id in member.unavailable and role != OFF:
                errors.append(f"{member.id}/{period.id}: unavailable but assigned {role}.")
            if role != OFF and role not in member.eligible_roles:
                errors.append(f"{member.id}/{period.id}: ineligible for {role}.")
            if role in member.forbidden_assignments.get(period.id, frozenset()):
                errors.append(f"{member.id}/{period.id}: forbidden assignment {role}.")
            fixed = member.fixed_assignments.get(period.id)
            if fixed is not None and fixed != role:
                errors.append(
                    f"{member.id}/{period.id}: fixed to {fixed}, assigned {role}."
                )
        for role in request.roles:
            required = period.requirements.get(role, 0)
            if counts[role] != required:
                errors.append(
                    f"{period.id}/{role}: requires {required}, assigned {counts[role]}."
                )

    for member in request.staff:
        counts = Counter(
            assignments.get(period.id, {}).get(member.id)
            for period in request.periods
        )
        for role, target in member.workload_targets.items():
            actual = (
                sum(counts[group_role] for group_role in request.role_groups[role])
                if role in request.role_groups
                else counts[role]
            )
            maximum = len(request.periods) if target.maximum is None else target.maximum
            if not target.minimum <= actual <= maximum:
                errors.append(
                    f"{member.id}/{role}: workload {actual} outside "
                    f"[{target.minimum}, {maximum}]."
                )

        for role in request.roles:
            limit = member.max_consecutive.get(
                role, request.rules.default_max_consecutive.get(role)
            )
            if limit is None:
                continue
            run = 0
            for period in request.periods:
                run = run + 1 if assignments[period.id][member.id] == role else 0
                if run > limit:
                    errors.append(
                        f"{member.id}/{role}: exceeds {limit} consecutive periods "
                        f"at {period.id}."
                    )
                    break

    unknown_periods = set(assignments) - set(period_by_id)
    if unknown_periods:
        errors.append(f"Assignments contain unknown periods {sorted(unknown_periods)}.")
    return errors
