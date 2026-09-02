import pandas as pd

file_path = "dataset/clean_customer_support_tickets.csv"

df = pd.read_csv(file_path)

print("\n========== CATEGORY EXAMPLES ==========\n")

for category in df["Ticket Type"].unique():
    print("\n-----------------------------------")
    print("CATEGORY:", category)
    print("-----------------------------------")

    rows = df[df["Ticket Type"] == category].head(5)

    for _, row in rows.iterrows():
        print("\nSubject:", row["Ticket Subject"])
        print("Description:", row["Ticket Description"])
        print("Query:", row["customer_query"])