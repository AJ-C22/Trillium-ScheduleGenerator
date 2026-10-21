from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

OFF = "OFF"


@dataclass(frozen=True)
class WorkloadTarget:
    minimum: int = 0
    maximum: int | None = None
    preferred: int | None = None
    weight: int = 10

    @classmethod
    def from_value(cls, value: int | dict[str, Any]) -> "WorkloadTarget":
        if isinstance(value, int):
            return cls(minimum=value, maximum=value, preferred=value)
        return cls(
            minimum=int(value.get("min", 0)),
            maximum=None if value.get("max") is None else int(value["max"]),
            preferred=None if value.get("preferred") is None else int(value["preferred"]),
            weight=int(value.get("weight", 10)),
        )


@dataclass(frozen=True)
class Preference:
    period: str
    role: str
    kind: str = "prefer"
    weight: int = 1

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Preference":
        return cls(
            period=str(data["period"]),
            role=str(data["role"]),
            kind=str(data.get("kind", "prefer")),
            weight=int(data.get("weight", 1)),
        )


@dataclass(frozen=True)
class Period:
    id: str
    label: str
    requirements: dict[str, int]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Period":
        period_id = str(data["id"])
        return cls(
            id=period_id,
            label=str(data.get("label", period_id)),
            requirements={str(role): int(count) for role, count in data["requirements"].items()},
        )


@dataclass(frozen=True)
class StaffMember:
    id: str
    name: str
    eligible_roles: frozenset[str]
    unavailable: frozenset[str] = frozenset()
    fixed_assignments: dict[str, str] = field(default_factory=dict)
    forbidden_assignments: dict[str, frozenset[str]] = field(default_factory=dict)
    workload_targets: dict[str, WorkloadTarget] = field(default_factory=dict)
    preferences: tuple[Preference, ...] = ()
    max_consecutive: dict[str, int] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any], all_roles: tuple[str, ...]) -> "StaffMember":
        staff_id = str(data["id"])
        eligible = data.get("eligible_roles", all_roles)
        return cls(
            id=staff_id,
            name=str(data.get("name", staff_id)),
            eligible_roles=frozenset(str(role) for role in eligible),
            unavailable=frozenset(str(period) for period in data.get("unavailable", [])),
            fixed_assignments={
                str(period): str(role) for period, role in data.get("fixed_assignments", {}).items()
            },
            forbidden_assignments={
                str(period): frozenset(str(role) for role in roles)
                for period, roles in data.get("forbidden_assignments", {}).items()
            },
            workload_targets={
                str(role): WorkloadTarget.from_value(value)
                for role, value in data.get("workload_targets", {}).items()
            },
            preferences=tuple(
                Preference.from_dict(preference) for preference in data.get("preferences", [])
            ),
            max_consecutive={
                str(role): int(limit) for role, limit in data.get("max_consecutive", {}).items()
            },
        )


@dataclass(frozen=True)
class ScheduleRules:
    default_max_consecutive: dict[str, int] = field(default_factory=dict)
    consecutive_assignment_weight: int = 1
    consecutive_role_weights: dict[str, int] = field(default_factory=dict)
    consecutive_off_weight: int = 4
    long_run_weight: int = 3
    time_limit_seconds: float = 60.0
    random_seed: int = 1

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScheduleRules":
        return cls(
            default_max_consecutive={
                str(role): int(limit)
                for role, limit in data.get("default_max_consecutive", {}).items()
            },
            consecutive_assignment_weight=int(data.get("consecutive_assignment_weight", 1)),
            consecutive_role_weights={
                str(role): int(weight)
                for role, weight in data.get("consecutive_role_weights", {}).items()
            },
            consecutive_off_weight=int(data.get("consecutive_off_weight", 4)),
            long_run_weight=int(data.get("long_run_weight", 3)),
            time_limit_seconds=float(data.get("time_limit_seconds", 60)),
            random_seed=int(data.get("random_seed", 1)),
        )


@dataclass(frozen=True)
class ScheduleRequest:
    name: str
    roles: tuple[str, ...]
    role_groups: dict[str, tuple[str, ...]]
    periods: tuple[Period, ...]
    staff: tuple[StaffMember, ...]
    rules: ScheduleRules = field(default_factory=ScheduleRules)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScheduleRequest":
        roles = tuple(str(role) for role in data["roles"])
        return cls(
            name=str(data.get("name", "Untitled schedule")),
            roles=roles,
            role_groups={
                str(group): tuple(str(role) for role in members)
                for group, members in data.get("role_groups", {}).items()
            },
            periods=tuple(Period.from_dict(period) for period in data["periods"]),
            staff=tuple(StaffMember.from_dict(member, roles) for member in data["staff"]),
            rules=ScheduleRules.from_dict(data.get("rules", {})),
        )


@dataclass(frozen=True)
class ScheduleResult:
    status: str
    assignments: dict[str, dict[str, str]]
    objective_value: float | None
    validation_errors: tuple[str, ...] = ()
    diagnostics: tuple[str, ...] = ()

    @property
    def is_success(self) -> bool:
        return self.status in {"OPTIMAL", "FEASIBLE"} and not self.validation_errors
