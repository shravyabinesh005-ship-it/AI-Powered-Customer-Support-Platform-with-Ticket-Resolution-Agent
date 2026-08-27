import pandas as pd

df = pd.read_csv("customer_support_tickets.csv")

print(df.head())
print(df.shape)
print(df.columns)
print(df.isnull().sum())
print("Duplicates:", df.duplicated().sum())
df = df.drop_duplicates()
df = df.drop(columns=[
    "Customer Name",
    "Customer Email"
], errors="ignore")
import re

def clean_text(text):
    if pd.isna(text):
        return ""

    text = str(text).lower()
    text = re.sub(r'[^\w\s]', '', text)
    text = text.strip()

    return text

df["Ticket Subject"] = df["Ticket Subject"].apply(clean_text)

df["Ticket Description"] = df["Ticket Description"].apply(clean_text)

df["Resolution"] = df["Resolution"].apply(clean_text)

df["customer_query"] = (
    df["Ticket Subject"] + " " +
    df["Ticket Description"]
)


df.to_csv("clean_customer_support_tickets.csv", index=False)

print("Dataset cleaned and saved!")