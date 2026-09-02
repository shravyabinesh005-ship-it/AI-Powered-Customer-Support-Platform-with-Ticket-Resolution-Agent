import pandas as pd

file_path = "dataset/clean_customer_support_tickets.csv"

df = pd.read_csv(file_path)

print("\nNumber of rows:", len(df))

print("\nColumn names:")
print(df.columns.tolist())

print("\nTicket Type values:")
print(df["Ticket Type"].value_counts())

print("\nFirst 5 rows:")
print(df.head())