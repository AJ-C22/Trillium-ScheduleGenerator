# Hospital Schedule Solver V1

V1 is a feasibility-first scheduling engine. It uses Google OR-Tools CP-SAT
instead of randomized assignment.

The engine will only return a schedule when every hard constraint is satisfied:

- exact coverage for every role and period
- one assignment or `OFF` per staff member and period
- availability
- role eligibility
- fixed assignments
- workload minimums and maximums
- configurable consecutive-assignment limits

Preferences, preferred workloads, and adjacent same-role assignments are
optimized only after those hard constraints are satisfied.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Run

```bash
python -m scheduler examples/basic_schedule.json
```

## Web application

```bash
source .venv/bin/activate
uvicorn web.app:app --reload
```

Open `http://127.0.0.1:8000`.

The web application supports configurable service lines and weekly coverage,
staff/FTE weighting, role eligibility, unavailable weeks, fixed assignments,
feasibility diagnostics, a 2D schedule matrix, local configuration
save/import, and CSV or formatted Excel export.

Realistic scale test:

```bash
python -m scheduler examples/standard_26_week.json \
  --output output/standard-26-week.csv \
  --report output/standard-26-week-report.json
```

This fixture contains 31 doctors, 26 weeks, and 15 required assignments per
week, matching the core scale of the reviewed workbooks.

Real 2026B workbook benchmark:

```bash
python tools/benchmark_2026b.py
```

This imports the current 2026B template and completed draft, solves all 26
weeks for the 31 core doctors, and writes:

- `examples/2026b_imported.json` — normalized machine-readable constraints
- `output/2026b-schedule.csv` — generated 2D schedule
- `output/2026b-report.json` — solver validation and workload totals
- `output/2026b-comparison.json` — comparison with the completed draft

The benchmark normalizes assignments to CTU, Inpatient, Clinic, ER, Consult,
Holiday Coverage, and OFF. Detailed service lines cannot yet be reconstructed
reliably because several completed workbook cells retain generic or request
labels instead of a specific line. External/locum coverage is reported
separately.

Outputs:

- `output/schedule.csv` — 2D matrix with staff names down the left, periods
  across the top, and assignments in the cells
- `output/report.json` — status, diagnostics, validation, and workloads

An infeasible request exits with status 2 and does not write a partial schedule.

## JSON input

The top-level fields are:

- `roles`: configurable role IDs
- `periods`: IDs, labels, and exact role requirements
- `staff`: eligibility, unavailable periods, fixed assignments, workload
  targets, preferences, and consecutive limits
- `rules`: organization-wide optimization and consecutive limits

See `examples/basic_schedule.json` for the complete V1 format.

Workload targets accept either an exact integer:

```json
{"CTU": 2}
```

or bounds with a soft preferred value:

```json
{"CTU": {"min": 1, "max": 3, "preferred": 2, "weight": 10}}
```

Preferences use `prefer` or `avoid`:

```json
{
  "period": "week-4",
  "role": "Clinic",
  "kind": "prefer",
  "weight": 5
}
```

Schedule-quality weights are configurable under `rules`:

- `consecutive_assignment_weight` penalizes the same working role in adjacent periods
- `consecutive_off_weight` spreads solver-selected off periods
- `long_run_weight` adds an extra penalty for runs of three identical assignments

Runs of preset unavailable periods remain hard constraints and are not penalized.
See `examples/preference_spacing.json` for an inspectable example.

## Current boundary

V1 solves the canonical model and the repository's legacy CSV fixture. Direct
Excel import and the full holiday/weekend semantics from the 2026 workbooks
are intentionally kept out of the solver core; they should be added as an
import/normalization layer once those ambiguous rules are confirmed.
