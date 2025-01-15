import csv
import pandas as pd

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
    return

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
    "Doctor 1": {"ER": 5, "Clinic": 4, "Off": 3},
    "Doctor 2": {"ER": 4, "Clinic": 5, "Off": 3},
    "Doctor 3": {"ER": 6, "Clinic": 3, "Off": 3},
}


schedule = {
    "Doctor 1": {"Sept 30 - Oct 6": "X", "Oct 7 - Oct 13": None, "Oct 14 - Oct 20": None, "Oct 21 - Oct 27": None},
    "Doctor 2": {"Sept 30 - Oct 6": None, "Oct 7 - Oct 13": "X", "Oct 14 - Oct 20": None, "Oct 21 - Oct 27": None},
    "Doctor 3": {"Sept 30 - Oct 6": None, "Oct 7 - Oct 13": None, "Oct 14 - Oct 20": "X", "Oct 21 - Oct 27": None},
}


weeks = {
    "Sept 30 - Oct 6": {"ER": 3, "Clinic": 2, "Off": 1},
    "Oct 7 - Oct 13": {"ER": 3, "Clinic": 2, "Off": 1},
    "Oct 14 - Oct 20": {"ER": 3, "Clinic": 2, "Off": 1},
    "Oct 21 - Oct 27": {"ER": 3, "Clinic": 2, "Off": 1},
}

for i in doctors:
    for j in doctors[i]:
        shifts[j] += int(doctors[i][j])

schedulify(schedule)

