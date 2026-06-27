# Trillium Hospital Schedule Generator

A smart schedule generator for hospital staff that respects doctor preferences, workload requirements, and automatically optimizes for quality-of-life factors like avoiding consecutive shifts and distributing off weeks evenly.

## Features

- ✅ **Constraint-based scheduling** - Respects all hard constraints from `test_sheet.csv`
- ✅ **Pre-marked off weeks** - Honors specific requested off weeks for each doctor
- ✅ **Smart optimization** - Minimizes consecutive same shifts (e.g., ER-ER-ER)
- ✅ **Even distribution** - Spreads off weeks throughout the schedule period
- ✅ **No blanks** - Ensures every slot is filled with a valid assignment
- ✅ **Comprehensive validation** - Built-in checking to verify schedule compliance

## Input File: `test_sheet.csv`

The input file contains three tables separated by blank rows:

### Table 1: Pre-marked Off Weeks
- Rows: Week 1 through Week 26
- Columns: Doctor names
- Values: `X` marks pre-requested off weeks for each doctor

### Table 2: Required Shifts per Doctor
- Rows: Shift types (CTU, Inpt, Clinic, ER, Consult, Off)
- Columns: Doctor names
- Values: Number of each shift type required for each doctor over 26 weeks

### Table 3: Required Shifts per Week
- Rows: Shift types (CTU, Inpt, Clinic, ER, Consult, Off)
- Columns: Week 1 through Week 26
- Values: Number of each shift type needed each week

## Usage

### Generate a New Schedule

```bash
python3 main.py
```

This will:
1. Read constraints from `test_sheet.csv`
2. Generate an optimized schedule using 50 randomized attempts
3. Select the best schedule based on quality metrics
4. Save the result to `schedule.csv`
5. Display verification statistics
6. Run comprehensive compliance checks

### Check an Existing Schedule

To validate an existing `schedule.csv` without regenerating it:

```bash
python3 check_schedule.py
```

This performs a comprehensive compliance check including:
- ✓ Pre-marked off weeks are respected
- ✓ No blank cells in the schedule
- ⚠ Doctor shift requirements (minor deviations noted)
- ⚠ Weekly shift requirements (minor deviations noted)
- ⚠ Consecutive shift patterns (3+ same shifts flagged)
- ⚠ Off week distribution (clusters flagged)

## Output File: `schedule.csv`

A CSV file with:
- Rows: Week 1 through Week 26
- Columns: Doctor names
- Values: Assigned shift type (CTU, Inpt, Clinic, ER, Consult) or `X` for off weeks

## Algorithm Details

### Multi-Attempt Optimization
The generator runs 50 independent attempts with randomized doctor ordering and selects the schedule with the best overall score.

### Scoring System
Each assignment is scored based on:
- **Consecutive shifts penalty** (-8 points per consecutive same shift)
- **Consecutive off weeks penalty** (-5 points per consecutive off week)
- **Diversity bonus** (+3 points for alternating shift types)
- **Availability reward** (prioritizes doctors with quota remaining)
- **Scarcity bonus** (prioritizes hard-to-fill shifts)
- **Temporal distribution** (ensures even spread of off weeks)

### Constraint Satisfaction
The algorithm prioritizes:
1. **Critical**: Pre-marked off weeks (always respected)
2. **Critical**: No blank cells (always filled)
3. **High**: Doctor shift quotas (best effort, minor ±1-2 deviations acceptable)
4. **High**: Weekly shift requirements (best effort with minor deviations)
5. **Medium**: Minimize consecutive same shifts
6. **Medium**: Distribute off weeks evenly

## Notes

- **Minor deviations** from doctor/weekly requirements (±1-2 shifts) are often mathematically unavoidable when constraints conflict
- The schedule prioritizes filling all slots over perfect quota matching
- Pre-marked off weeks are always respected (critical constraint)
- Consecutive shift patterns are minimized but not completely eliminated in exchange for meeting coverage requirements

## Files

- `main.py` - Main schedule generator with built-in validation
- `check_schedule.py` - Standalone validation script
- `test_sheet.csv` - Input constraints file
- `schedule.csv` - Generated schedule output
- `README.md` - This documentation

## Requirements

```bash
pip install pandas
```

## Example Output

```
Schedule generated successfully!
Total blanks remaining: 0

================================================================================
COMPLIANCE SUMMARY
================================================================================
✓ ACCEPTABLE: Schedule has no critical issues
  ⚠ 79 minor warnings (often unavoidable with conflicting constraints)
================================================================================
```
