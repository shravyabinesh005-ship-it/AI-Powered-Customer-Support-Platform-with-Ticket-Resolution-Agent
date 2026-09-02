import pandas as pd

file_path = "dataset/helpdesk_tickets.csv"

df = pd.read_csv(file_path)

print("\n========== HELP DESK DATASET ==========")

print("\nNumber of rows:", len(df))

print("\nColumn names:")
print(df.columns.tolist())

print("\nFirst 5 rows:")
print(df.head())

print("\n========== UNIQUE VALUES ==========")

for column in df.columns:
    if df[column].nunique() <= 20:
        print(f"\n{column}:")
        print(df[column].value_counts())
        