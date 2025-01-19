import csv
import pandas as pd
import random 

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

    for week, week_requirements in weeks.items():
        remaining_requirements = week_requirements.copy()
        for doctor, shifts in schedule.items():
            if shifts.get(week) == "X":
                continue
            #Maybe subtract from "Off" if "Off" includes the designated weeks off
            #shift_types = ["CTU", "Input", "Clinic", "ER", "Consult", "Off"]
            shift_types = ["Clinic", "ER", "Off"]
            random.shuffle(shift_types)
            for shift_type in shift_types:
                
                if (
                    remaining_requirements[shift_type] > 0
                    and doctor_availability[doctor][shift_type] > 0
                ):
                    print(doctor)
                    print(week)
                    print()
                    schedule[doctor][week] = shift_type
                    remaining_requirements[shift_type] -= 1
                    doctor_availability[doctor][shift_type] -= 1
                    break

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
    "Doctor 1": {"ER": 3, "Clinic": 2, "Off": 2},
    "Doctor 2": {"ER": 3, "Clinic": 3, "Off": 1},
    "Doctor 3": {"ER": 3, "Clinic": 3, "Off": 1},
    "Doctor 4": {"ER": 2, "Clinic": 4, "Off": 2},
    "Doctor 5": {"ER": 4, "Clinic": 2, "Off": 2},
    "Doctor 6": {"ER": 3, "Clinic": 3, "Off": 1},
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
    "Week 1": {"ER": 3, "Clinic": 3, "Off": 2},
    "Week 2": {"ER": 3, "Clinic": 3, "Off": 2},
    "Week 3": {"ER": 3, "Clinic": 3, "Off": 2},
    "Week 4": {"ER": 3, "Clinic": 3, "Off": 2},
    "Week 5": {"ER": 3, "Clinic": 3, "Off": 2},
    "Week 6": {"ER": 3, "Clinic": 3, "Off": 2},
    "Week 7": {"ER": 3, "Clinic": 3, "Off": 2},
    "Week 8": {"ER": 3, "Clinic": 3, "Off": 2},
    "Week 9": {"ER": 3, "Clinic": 3, "Off": 2},
    "Week 10": {"ER": 3, "Clinic": 3, "Off": 2},
}

for i in doctors:
    for j in doctors[i]:
        shifts[j] += int(doctors[i][j])

schedulify(fill_schedule(doctors,schedule,weeks))

