import csv
import pandas as pd
import random 
from collections import Counter

shifts = {"CTU": 0, "Input": 0, "Clinic": 0, "ER": 0, "Consult": 0, "Off": 0 }
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

def fill_schedule(doctors, schedule, weeks):
    doctor_availability = {doc: shifts.copy() for doc, shifts in doctors.items()}
    
    def calculate_score(doctor, shift_type, week, current_schedule):
        week_list = list(current_schedule[doctor].keys())
        week_index = week_list.index(week)
        score = 0

        # Penalize consecutive shifts
        if week_index > 0 and current_schedule[doctor][week_list[week_index - 1]] == shift_type:
            score -= 2  # Heavier penalty for immediate consecutive shifts
        if week_index > 1 and current_schedule[doctor][week_list[week_index - 2]] == shift_type:
            score -= 1  # Slight penalty for shift occurring two weeks ago

        # Reward shifts that break consecutive patterns
        if week_index > 0 and current_schedule[doctor][week_list[week_index - 1]] != shift_type:
            score += 1  # Reward diversity in shifts

        # Reward doctors with higher availability for this shift
        score += doctor_availability[doctor][shift_type]

        return score

    for week, week_requirements in weeks.items():
        remaining_requirements = week_requirements.copy()

        # Shuffle doctors to introduce variability in the schedule
        doctor_order = list(schedule.keys())
        random.shuffle(doctor_order)

        for doctor in doctor_order:
            if schedule[doctor][week] == "X":  # Handle mandatory off weeks
                remaining_requirements["Off"] -= 1
                doctor_availability[doctor]["Off"] -= 1
                continue

            shift_types = ["ER", "Clinic", "Off"]
            best_shift = None
            best_score = float('-inf')
            
            for shift_type in shift_types:
                if remaining_requirements[shift_type] > 0 and doctor_availability[doctor][shift_type] > 0:
                    score = calculate_score(doctor, shift_type, week, schedule)
                    if score > best_score:
                        best_score = score
                        best_shift = shift_type

            if best_shift:
                if best_shift == "Off":
                    schedule[doctor][week] = "X"
                else:
                    schedule[doctor][week] = best_shift

                remaining_requirements[best_shift] -= 1
                doctor_availability[doctor][best_shift] -= 1

    return schedule

def schedulify(d):
    print()
    for i in d:
        print(i + ":\n")
        for j in d[i]:
            if d[i][j]:
                print(j + " : " + d[i][j])
            else: 
                print(j + ': N/A')
        print()      

    return 

#----------------------------------------------------------------#
'''
doctors = get_dict(table1)
schedule = get_dict(table2)
weeks = get_dict(table3)
'''

doctors = {
    "Doctor 1": {"ER": 4, "Clinic": 3, "Off": 3},
    "Doctor 2": {"ER": 3, "Clinic": 3, "Off": 4},
    "Doctor 3": {"ER": 3, "Clinic": 4, "Off": 3},
    "Doctor 4": {"ER": 4, "Clinic": 2, "Off": 4},
    "Doctor 5": {"ER": 3, "Clinic": 4, "Off": 3},
    "Doctor 6": {"ER": 3, "Clinic": 4, "Off": 3},
}

schedule = {
    "Doctor 1": {"Week 1": "X", "Week 2": None, "Week 3": None, "Week 4": None, "Week 5": None, "Week 6": None, "Week 7": None, "Week 8": None, "Week 9": None, "Week 10": None},
    "Doctor 2": {"Week 1": None, "Week 2": "X", "Week 3": None, "Week 4": None, "Week 5": None, "Week 6": None, "Week 7": None, "Week 8": None, "Week 9": None, "Week 10": None},
    "Doctor 3": {"Week 1": None, "Week 2": None, "Week 3": "X", "Week 4": None, "Week 5": None, "Week 6": None, "Week 7": None, "Week 8": None, "Week 9": None, "Week 10": None},
    "Doctor 4": {"Week 1": None, "Week 2": None, "Week 3": None, "Week 4": None, "Week 5": None, "Week 6": None, "Week 7": None, "Week 8": None, "Week 9": None, "Week 10": None},
    "Doctor 5": {"Week 1": None, "Week 2": None, "Week 3": None, "Week 4": None, "Week 5": None, "Week 6": None, "Week 7": None, "Week 8": None, "Week 9": None, "Week 10": None},
    "Doctor 6": {"Week 1": None, "Week 2": None, "Week 3": None, "Week 4": None, "Week 5": None, "Week 6": None, "Week 7": None, "Week 8": None, "Week 9": None, "Week 10": None},
}

weeks = {
    # 20 ER, 20 CLINIC, 20 OFF
    "Week 1": {"ER": 2, "Clinic": 2, "Off": 2},
    "Week 2": {"ER": 2, "Clinic": 2, "Off": 2},
    "Week 3": {"ER": 2, "Clinic": 2, "Off": 2},
    "Week 4": {"ER": 2, "Clinic": 2, "Off": 2},
    "Week 5": {"ER": 2, "Clinic": 2, "Off": 2},
    "Week 6": {"ER": 2, "Clinic": 2, "Off": 2},
    "Week 7": {"ER": 2, "Clinic": 2, "Off": 2},
    "Week 8": {"ER": 2, "Clinic": 2, "Off": 2},
    "Week 9": {"ER": 2, "Clinic": 2, "Off": 2},
    "Week 10": {"ER": 2, "Clinic": 2, "Off": 2},
}

for i in doctors:
    for j in doctors[i]:
        shifts[j] += int(doctors[i][j])

schedulify(fill_schedule(doctors,schedule,weeks))

