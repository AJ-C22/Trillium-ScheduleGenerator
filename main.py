import csv
import pandas as pd

file_path = "test_sheet.csv"
df = pd.read_csv(file_path, header = None)

split_index = df[df.isna().all(axis=1)].index[0]
table1 = df.iloc[:split_index].dropna(axis=1, how="all")  
table2 = df.iloc[split_index + 1:].dropna(axis=1, how="all")

print(table1)
print(table2)