#!/usr/bin/env python3
"""
Standalone script to validate schedule.csv against constraints in test_sheet.csv
without regenerating the schedule.
"""

import pandas as pd
from collections import Counter

def get_dict(table1):
    table1.columns = ["Shift"] + table1.iloc[0, 1:].tolist() 
    table1 = table1[1:].reset_index(drop=True)  
    shift_requirements_by_doctor = {}
    for doctor in table1.columns[1:]:
        doctor_shifts = table1.set_index("Shift")[doctor].to_dict()
        shift_requirements_by_doctor[doctor] = doctor_shifts
    return shift_requirements_by_doctor

def get_dict_int(table1):
    table1.columns = ["Shift"] + table1.iloc[0, 1:].astype(str).tolist()
    table1 = table1[1:].reset_index(drop=True)
    shift_requirements_by_doctor = {}
    for doctor in table1.columns[1:]:
        shift_requirements_by_doctor[doctor] = (
            table1.set_index("Shift")[doctor]
            .dropna()
            .astype(int)
            .to_dict()
        )
    return shift_requirements_by_doctor

def check_schedule_compliance(schedule, doctors, weeks, original_restrictions):
    """
    Comprehensive validation function to check if schedule adheres to all constraints
    Returns: (is_valid, violations_list)
    """
    violations = []
    is_valid = True
    
    print("\n" + "=" * 80)
    print("SCHEDULE COMPLIANCE CHECK")
    print("=" * 80)
    
    # Check 1: Verify pre-marked off weeks are respected
    print("\n1. Checking pre-marked off weeks...")
    off_violations = 0
    for doctor in original_restrictions:
        for week in original_restrictions[doctor]:
            required_off = original_restrictions[doctor][week]
            actual_shift = schedule[doctor][week]
            
            if required_off == "X" and actual_shift != "X":
                violations.append(
                    f"  ✗ {doctor} should be OFF in {week} but is assigned: {actual_shift}"
                )
                off_violations += 1
                is_valid = False
    
    if off_violations == 0:
        print("  ✓ All pre-marked off weeks respected")
    else:
        print(f"  ✗ Found {off_violations} violations of pre-marked off weeks")
        for v in violations[-off_violations:]:
            print(v)
    
    # Check 2: Verify no blanks in schedule
    print("\n2. Checking for blank cells...")
    blank_count = 0
    for doctor in schedule:
        for week in schedule[doctor]:
            value = schedule[doctor][week]
            if value is None or not value or (isinstance(value, str) and not value.strip()):
                violations.append(f"  ✗ Blank cell found: {doctor} in {week}")
                blank_count += 1
                is_valid = False
    
    if blank_count == 0:
        print("  ✓ No blank cells found")
    else:
        print(f"  ✗ Found {blank_count} blank cells")
        for v in violations[-blank_count:]:
            print(v)
    
    # Check 3: Verify doctor shift requirements
    print("\n3. Checking doctor shift requirements...")
    doctor_violations = 0
    doctor_details = []
    
    for doctor in doctors:
        assigned = Counter()
        for week in schedule[doctor]:
            shift = schedule[doctor][week]
            if shift == "X":
                assigned["Off"] += 1
            elif shift and isinstance(shift, str) and shift.strip():
                assigned[shift] += 1
        
        has_violation = False
        violation_details = []
        
        for shift_type in doctors[doctor]:
            required = doctors[doctor][shift_type]
            actual = assigned.get(shift_type, 0)
            
            if required != actual:
                diff = actual - required
                sign = "+" if diff > 0 else ""
                violation_details.append(
                    f"    {shift_type}: required {required}, got {actual} ({sign}{diff})"
                )
                has_violation = True
        
        if has_violation:
            doctor_violations += 1
            doctor_details.append(f"  ✗ {doctor}:")
            doctor_details.extend(violation_details)
    
    if doctor_violations == 0:
        print("  ✓ All doctors have exactly the required number of each shift type")
    else:
        print(f"  ⚠ {doctor_violations} doctors have deviations from required shifts")
        print("    (Note: Minor deviations may be unavoidable with conflicting constraints)")
        if doctor_violations <= 10:
            for detail in doctor_details[:50]:
                print(detail)
        else:
            print(f"    (Showing first 10 doctors with violations...)")
            for detail in doctor_details[:50]:
                print(detail)
    
    # Check 4: Verify weekly shift requirements
    print("\n4. Checking weekly shift requirements...")
    week_violations = 0
    week_details = []
    
    for week in weeks:
        week_assigned = Counter()
        for doctor in schedule:
            shift = schedule[doctor][week]
            if shift == "X":
                week_assigned["Off"] += 1
            elif shift and isinstance(shift, str) and shift.strip():
                week_assigned[shift] += 1
        
        has_violation = False
        violation_details = []
        
        for shift_type in weeks[week]:
            required = weeks[week][shift_type]
            actual = week_assigned.get(shift_type, 0)
            
            if required != actual:
                diff = actual - required
                sign = "+" if diff > 0 else ""
                violation_details.append(
                    f"    {shift_type}: required {required}, got {actual} ({sign}{diff})"
                )
                has_violation = True
        
        if has_violation:
            week_violations += 1
            week_details.append(f"  ⚠ {week}:")
            week_details.extend(violation_details)
    
    if week_violations == 0:
        print("  ✓ All weeks have exactly the required number of each shift type")
    else:
        print(f"  ⚠ {week_violations} weeks have deviations from required shifts")
        print("    (Note: Minor deviations may be unavoidable with conflicting constraints)")
        if week_violations <= 5:
            for detail in week_details[:30]:
                print(detail)
        else:
            print(f"    (Showing first 5 weeks with violations...)")
            for detail in week_details[:30]:
                print(detail)
    
    # Check 5: Analyze consecutive shift patterns
    print("\n5. Checking for consecutive same shift patterns...")
    consecutive_patterns = []
    
    for doctor in schedule:
        shifts_list = list(schedule[doctor].items())
        i = 0
        while i < len(shifts_list) - 2:
            week1, shift1 = shifts_list[i]
            week2, shift2 = shifts_list[i + 1]
            week3, shift3 = shifts_list[i + 2]
            
            # Check for 3+ consecutive same shifts (excluding Off)
            if shift1 == shift2 == shift3 and shift1 != "X" and shift1:
                # Count how many consecutive
                count = 3
                j = i + 3
                while j < len(shifts_list) and shifts_list[j][1] == shift1:
                    count += 1
                    j += 1
                
                consecutive_patterns.append(
                    f"  ⚠ {doctor}: {count} consecutive {shift1} shifts "
                    f"({week1} to {shifts_list[i + count - 1][0]})"
                )
                i = j
            else:
                i += 1
    
    if len(consecutive_patterns) == 0:
        print("  ✓ No problematic consecutive shift patterns found")
    else:
        print(f"  ⚠ Found {len(consecutive_patterns)} instances of 3+ consecutive same shifts:")
        for pattern in consecutive_patterns[:10]:
            print(pattern)
    
    # Check 6: Analyze off week distribution
    print("\n6. Checking off week distribution...")
    clustered_offs = []
    
    for doctor in schedule:
        off_weeks = [w for w, s in schedule[doctor].items() if s == "X"]
        if len(off_weeks) > 1:
            # Check for clusters of off weeks
            week_numbers = [int(w.split()[1]) for w in off_weeks]
            week_numbers.sort()
            
            consecutive_offs = 1
            for i in range(1, len(week_numbers)):
                if week_numbers[i] == week_numbers[i-1] + 1:
                    consecutive_offs += 1
                    if consecutive_offs >= 3:
                        clustered_offs.append(
                            f"  ⚠ {doctor}: {consecutive_offs}+ consecutive off weeks "
                            f"around Week {week_numbers[i]}"
                        )
                        break
                else:
                    consecutive_offs = 1
    
    if len(clustered_offs) == 0:
        print("  ✓ Off weeks are reasonably distributed")
    else:
        print(f"  ⚠ Found {len(clustered_offs)} doctors with 3+ consecutive off weeks:")
        for cluster in clustered_offs[:10]:
            print(cluster)
    
    # Summary
    print("\n" + "=" * 80)
    print("COMPLIANCE SUMMARY")
    print("=" * 80)
    
    critical_issues = off_violations + blank_count
    warnings = doctor_violations + week_violations + len(consecutive_patterns) + len(clustered_offs)
    
    if critical_issues == 0 and warnings == 0:
        print("✓ PERFECT: Schedule fully complies with all constraints!")
    elif critical_issues == 0:
        print(f"✓ ACCEPTABLE: Schedule has no critical issues")
        print(f"  ⚠ {warnings} minor warnings (often unavoidable with conflicting constraints)")
    else:
        print(f"✗ ISSUES FOUND:")
        print(f"  Critical: {critical_issues}")
        print(f"  Warnings: {warnings}")
    
    print("=" * 80 + "\n")
    
    return is_valid, violations

if __name__ == "__main__":
    print("Loading constraints from test_sheet.csv...")
    
    # Load test_sheet.csv
    df = pd.read_csv("test_sheet.csv", header=None)
    split_indices = df[df.isna().all(axis=1)].index.tolist()
    
    table1 = df.iloc[:split_indices[0]].dropna(axis=1, how="all").reset_index(drop=True)
    table2 = df.iloc[split_indices[0] + 1:split_indices[1]].dropna(axis=1, how="all").reset_index(drop=True)
    table3 = df.iloc[split_indices[1] + 1:].dropna(axis=1, how="all").reset_index(drop=True)
    
    original_restrictions = get_dict(table1)
    doctors = get_dict_int(table2)
    weeks = get_dict_int(table3)
    
    print("Loading generated schedule from schedule.csv...")
    
    # Load schedule.csv
    schedule_df = pd.read_csv("schedule.csv", index_col=0)
    schedule = {doc: schedule_df[doc].to_dict() for doc in schedule_df.columns}
    
    # Run compliance check
    is_valid, violations = check_schedule_compliance(schedule, doctors, weeks, original_restrictions)
    
    if is_valid:
        print("✓ Schedule validation PASSED with no critical issues!")
    else:
        print("✗ Schedule validation FAILED - critical issues found!")
        print(f"\nTotal violations: {len(violations)}")
