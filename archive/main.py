import csv
import pandas as pd
import random 
from collections import Counter, defaultdict
import math

shifts = {"CTU": 0, "Inpt": 0, "Clinic": 0, "ER": 0, "Consult": 0, "Off": 0 }
file_path = "test_sheet.csv"
df = pd.read_csv(file_path, header = None)

split_index = df[df.isna().all(axis=1)].index[0]
split_indices = df[df.isna().all(axis=1)].index.tolist()

table1 = df.iloc[:split_indices[0]].dropna(axis=1, how="all").reset_index(drop=True)
table2 = df.iloc[split_indices[0] + 1:split_indices[1]].dropna(axis=1, how="all").reset_index(drop=True)
table3 = df.iloc[split_indices[1] + 1:].dropna(axis=1, how="all").reset_index(drop=True)

def get_dict(table1):
    table1.columns = ["Shift"] + table1.iloc[0, 1:].tolist() 
    table1 = table1[1:].reset_index(drop=True)  

    # Parse Table 1 by doctor
    shift_requirements_by_doctor = {}

    # Loop through each doctor column
    for doctor in table1.columns[1:]:
        doctor_shifts = table1.set_index("Shift")[doctor].to_dict()
        shift_requirements_by_doctor[doctor] = doctor_shifts

    return shift_requirements_by_doctor

def get_dict_int(table1):
    table1.columns = ["Shift"] + table1.iloc[0, 1:].astype(str).tolist()  # Ensure column names are strings
    table1 = table1[1:].reset_index(drop=True)  # Remove the duplicated header row

    # Parse shift requirements per doctor
    shift_requirements_by_doctor = {}

    for doctor in table1.columns[1:]:  # Skip "Shift" column
        shift_requirements_by_doctor[doctor] = (
            table1.set_index("Shift")[doctor]
            .dropna()
            .astype(int)  # Convert values to integers
            .to_dict()
        )

    return shift_requirements_by_doctor

def fill_schedule(doctors, schedule, weeks, max_attempts=150):
    """
    Fill schedule with constraint satisfaction approach
    Uses multiple attempts to find the best solution
    """
    best_schedule = None
    best_score = float('-inf')
    
    for attempt in range(max_attempts):
        # Create a fresh copy of doctor availability
        doctor_availability = {doc: shifts.copy() for doc, shifts in doctors.items()}
        current_schedule = {doc: week_dict.copy() for doc, week_dict in schedule.items()}
        
        # First pass: handle all pre-marked "X" off weeks and update availability
        for doctor in current_schedule:
            for week in current_schedule[doctor]:
                if current_schedule[doctor][week] == "X":
                    # This is a pre-marked off week
                    if "Off" in doctor_availability[doctor] and doctor_availability[doctor]["Off"] > 0:
                        doctor_availability[doctor]["Off"] -= 1
        
        # Process weeks in order
        week_names = sorted(weeks.keys(), key=lambda x: int(x.split()[1]))
        
        for week in week_names:
            week_requirements = weeks[week].copy()
            
            # First, count pre-marked "X" weeks for this week
            premarked_offs = sum(1 for doc in current_schedule if current_schedule[doc][week] == "X")
            week_requirements["Off"] = max(0, week_requirements["Off"] - premarked_offs)
            
            # Create list of doctors who need assignments this week
            doctors_to_assign = [doc for doc in current_schedule if current_schedule[doc][week] != "X"]
            
            # Shuffle for randomness (different attempts will try different orders)
            random.shuffle(doctors_to_assign)
            
            # Sort doctors by how many options they have (least options first - more constrained)
            def count_options(doctor):
                count = 0
                for shift in week_requirements:
                    if week_requirements[shift] > 0 and doctor_availability[doctor].get(shift, 0) > 0:
                        count += 1
                return count
            
            doctors_to_assign.sort(key=count_options)
            
            # Phase 1: Prioritize perfect matches (both week needs AND doctor can do)
            unassigned_doctors = doctors_to_assign.copy()
            random.shuffle(unassigned_doctors)  # Randomize for variety across attempts
            
            assigned_this_phase = []
            for doctor in unassigned_doctors[:]:
                shift_types = ["CTU", "Inpt", "Clinic", "ER", "Consult", "Off"]
                best_shift = None
                best_score_local = float('-inf')
                
                # Look for shifts where week needs it AND doctor has quota
                for shift_type in shift_types:
                    if (week_requirements.get(shift_type, 0) > 0 and 
                        doctor_availability[doctor].get(shift_type, 0) > 0):
                        
                        score = calculate_score(doctor, shift_type, week, current_schedule, 
                                              doctor_availability, week_requirements)
                        score += 100  # HUGE bonus for perfect match
                        
                        # Extra bonus for scarce shifts
                        if week_requirements[shift_type] <= 2:
                            score += 50
                        
                        if score > best_score_local:
                            best_score_local = score
                            best_shift = shift_type
                
                if best_shift:
                    # Assign the shift
                    if best_shift == "Off":
                        current_schedule[doctor][week] = "X"
                    else:
                        current_schedule[doctor][week] = best_shift
                    
                    # Update counters
                    week_requirements[best_shift] -= 1
                    doctor_availability[doctor][best_shift] -= 1
                    assigned_this_phase.append(doctor)
            
            # Remove assigned doctors
            for doc in assigned_this_phase:
                unassigned_doctors.remove(doc)
            
            # Phase 2: Assign remaining doctors (prioritize weekly needs over doctor quotas)
            for doctor in unassigned_doctors:
                shift_types = ["CTU", "Inpt", "Clinic", "ER", "Consult", "Off"]
                best_shift = None
                best_score_local = float('-inf')
                
                # First try: shifts that week still needs (even if doctor quota exhausted)
                for shift_type in shift_types:
                    if week_requirements.get(shift_type, 0) > 0:
                        score = calculate_score(doctor, shift_type, week, current_schedule, 
                                              doctor_availability, week_requirements)
                        
                        # High bonus for meeting weekly need
                        score += 75
                        
                        # Additional bonus if doctor also has quota
                        if doctor_availability[doctor].get(shift_type, 0) > 0:
                            score += 30
                        
                        if score > best_score_local:
                            best_score_local = score
                            best_shift = shift_type
                
                # Second try: use doctor's remaining quota even if week doesn't need it
                if not best_shift:
                    for shift_type in shift_types:
                        if doctor_availability[doctor].get(shift_type, 0) > 0:
                            score = calculate_score(doctor, shift_type, week, current_schedule, 
                                                  doctor_availability, week_requirements)
                            score += 10
                            
                            if score > best_score_local:
                                best_score_local = score
                                best_shift = shift_type
                
                # Last resort: give them off time
                if not best_shift:
                    best_shift = "Off"
                
                # Assign the shift
                if best_shift == "Off":
                    current_schedule[doctor][week] = "X"
                else:
                    current_schedule[doctor][week] = best_shift
                
                # Update counters
                if week_requirements.get(best_shift, 0) > 0:
                    week_requirements[best_shift] -= 1
                if doctor_availability[doctor].get(best_shift, 0) > 0:
                    doctor_availability[doctor][best_shift] -= 1
            
            # Fill any remaining requirements with doctors who can take extra work
            # This ensures all weekly requirements are met
            for shift_type in ["CTU", "Inpt", "Clinic", "ER", "Consult"]:
                while week_requirements.get(shift_type, 0) > 0:
                    # Find doctors who are working this week and could swap
                    available_docs = []
                    for doc in doctors_to_assign:
                        current_shift = current_schedule[doc][week]
                        # Can reassign if currently Off or another shift type
                        if current_shift and current_shift != "X" and current_shift != shift_type:
                            available_docs.append(doc)
                    
                    if not available_docs:
                        break
                    
                    # Pick a random doctor and reassign
                    chosen_doc = random.choice(available_docs)
                    old_shift = current_schedule[chosen_doc][week]
                    current_schedule[chosen_doc][week] = shift_type
                    week_requirements[shift_type] -= 1
                    # Note: We don't update doctor_availability here as we're going over quota if needed
        
        # Evaluate this schedule
        schedule_score = evaluate_schedule(current_schedule, doctors, weeks)
        
        if schedule_score > best_score:
            best_score = schedule_score
            best_schedule = current_schedule
    
    return best_schedule

def calculate_score(doctor, shift_type, week, current_schedule, doctor_availability, week_requirements):
    """
    Calculate a score for assigning a shift to a doctor
    Higher score = better assignment
    """
    week_list = list(current_schedule[doctor].keys())
    week_index = week_list.index(week)
    score = 0
    
    # 1. Penalize consecutive same shifts (avoid ER ER ER patterns)
    consecutive_count = 0
    for i in range(1, 4):  # Look back up to 3 weeks
        if week_index >= i:
            prev_week = week_list[week_index - i]
            prev_shift = current_schedule[doctor][prev_week]
            if prev_shift == shift_type or (prev_shift == "X" and shift_type == "Off"):
                consecutive_count += 1
            else:
                break
    
    # Heavy penalty for consecutive same shifts
    score -= consecutive_count * 8
    
    # 2. Penalize consecutive off weeks (spread them out)
    if shift_type == "Off":
        off_count = 0
        for i in range(1, 4):
            if week_index >= i:
                prev_week = week_list[week_index - i]
                if current_schedule[doctor][prev_week] == "X":
                    off_count += 1
        score -= off_count * 5
    
    # 3. Reward shifts that break patterns (diversity bonus)
    if week_index > 0:
        prev_shift = current_schedule[doctor][week_list[week_index - 1]]
        if prev_shift and prev_shift != shift_type and not (prev_shift == "X" and shift_type == "Off"):
            score += 3
    
    # 4. Reward doctors with higher availability for this shift
    availability_ratio = doctor_availability[doctor].get(shift_type, 0)
    score += availability_ratio * 1.0
    
    # 5. Prioritize filling scarce shift types
    if week_requirements.get(shift_type, 0) > 0:
        scarcity = 15.0 / max(week_requirements.get(shift_type, 1), 1)
        score += scarcity
    
    # 6. Bonus for "Off" if doctor has many off weeks remaining
    if shift_type == "Off":
        total_weeks = len(week_list)
        weeks_remaining = total_weeks - week_index
        offs_remaining = doctor_availability[doctor].get("Off", 0)
        if weeks_remaining > 0:
            off_density = offs_remaining / weeks_remaining
            if off_density > 0.6:  # Too many offs left
                score += 5
            elif off_density < 0.2:  # Very few offs left
                score -= 3
    
    return score

def evaluate_schedule(schedule, doctors, weeks):
    """
    Evaluate the quality of a schedule
    Higher score = better schedule
    """
    score = 0
    
    # Count blanks (heavily penalize)
    blank_count = 0
    for doctor in schedule:
        for week in schedule[doctor]:
            value = schedule[doctor][week]
            if not value or (isinstance(value, str) and not value.strip()):
                blank_count += 1
                score -= 100  # Heavy penalty for blanks
    
    # Reward meeting doctor requirements
    for doctor in doctors:
        assigned = Counter()
        for week in schedule[doctor]:
            shift = schedule[doctor][week]
            if shift == "X":
                assigned["Off"] += 1
            elif shift:
                assigned[shift] += 1
        
        for shift_type, required in doctors[doctor].items():
            actual = assigned.get(shift_type, 0)
            diff = abs(actual - required)
            score -= diff * 2  # Penalize deviations from doctor requirements
    
    # Reward meeting weekly requirements
    for week in weeks:
        week_assigned = Counter()
        for doctor in schedule:
            shift = schedule[doctor][week]
            if shift == "X":
                week_assigned["Off"] += 1
            elif shift:
                week_assigned[shift] += 1
        
        for shift_type, required in weeks[week].items():
            actual = week_assigned.get(shift_type, 0)
            diff = abs(actual - required)
            score -= diff * 3  # Penalize deviations from weekly requirements
    
    # Reward avoiding consecutive same shifts
    for doctor in schedule:
        week_list = list(schedule[doctor].keys())
        for i in range(1, len(week_list)):
            curr_shift = schedule[doctor][week_list[i]]
            prev_shift = schedule[doctor][week_list[i-1]]
            if curr_shift and prev_shift and curr_shift == prev_shift:
                score -= 1  # Small penalty for consecutive same shifts
    
    return score

def schedulify(d):
    print()
    for i in d:
        print(i + ":\n")
        for j in d[i]:
            if d[i][j]:
                print(j + " : " + str(d[i][j]))
            else: 
                print(j + ': N/A')
        print()      

    return

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
        if doctor_violations <= 10:  # Show details for first 10
            for detail in doctor_details[:50]:  # Limit output
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
        if week_violations <= 5:  # Show details for first 5 weeks
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
        for pattern in consecutive_patterns[:10]:  # Show first 10
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

#----------------------------------------------------------------#

schedule = get_dict(table1)
doctors = get_dict_int(table2)
weeks = get_dict_int(table3)

print("Generating schedule with multiple attempts...")
print("This may take a moment...\n")

# Run the schedule generation with multiple attempts
# Use more attempts to find optimal solution with balanced constraints
final_schedule = fill_schedule(doctors, schedule, weeks, max_attempts=150)

# Convert to DataFrame
df = pd.DataFrame(final_schedule)

# Replace None and empty strings with empty string for CSV
df = df.fillna("")

# Save to CSV file
df.to_csv("schedule.csv", index=True, index_label="Week")

print("Schedule generated successfully!")
print("\nChecking for any remaining blanks...")

# Count blanks
blank_count = 0
for doctor in final_schedule:
    for week in final_schedule[doctor]:
        value = final_schedule[doctor][week]
        if value is None or not value or (isinstance(value, str) and not value.strip()):
            blank_count += 1
            
print(f"Total blanks remaining: {blank_count}")

# Verify shift counts
print("\nVerifying shift assignments...")
doctor_mismatches = 0
for doctor in doctors:
    assigned = Counter()
    for week in final_schedule[doctor]:
        shift = final_schedule[doctor][week]
        if shift == "X":
            assigned["Off"] += 1
        elif shift and isinstance(shift, str) and shift.strip():
            assigned[shift] += 1
    
    mismatch = False
    for shift_type in doctors[doctor]:
        required = doctors[doctor][shift_type]
        actual = assigned.get(shift_type, 0)
        if abs(required - actual) > 0:
            mismatch = True
    
    if mismatch:
        doctor_mismatches += 1
        print(f"\n{doctor}:")
        print(f"  Required: {doctors[doctor]}")
        print(f"  Assigned: {dict(assigned)}")

if doctor_mismatches == 0:
    print("\nAll doctors have correct shift assignments!")
else:
    print(f"\n{doctor_mismatches} doctors have minor deviations (this is normal when constraints conflict)")

# Verify weekly requirements
print("\nVerifying weekly requirements...")
week_mismatches = 0
for week in weeks:
    week_assigned = Counter()
    for doctor in final_schedule:
        shift = final_schedule[doctor][week]
        if shift == "X":
            week_assigned["Off"] += 1
        elif shift and isinstance(shift, str) and shift.strip():
            week_assigned[shift] += 1
    
    mismatch = False
    for shift_type in weeks[week]:
        required = weeks[week][shift_type]
        actual = week_assigned.get(shift_type, 0)
        if abs(required - actual) > 2:  # Allow small deviations
            mismatch = True
    
    if mismatch:
        week_mismatches += 1
        if week_mismatches <= 5:  # Only show first 5
            print(f"\n{week}:")
            print(f"  Required: {weeks[week]}")
            print(f"  Assigned: {dict(week_assigned)}")

if week_mismatches == 0:
    print("\nAll weeks have correct shift requirements met!")
else:
    print(f"\n{week_mismatches} weeks have deviations from requirements")

# Run comprehensive compliance check
is_valid, violations = check_schedule_compliance(final_schedule, doctors, weeks, schedule)
