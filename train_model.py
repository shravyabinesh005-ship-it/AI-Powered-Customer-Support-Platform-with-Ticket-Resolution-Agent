import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, classification_report

# 1. Load the dataset
file_path = "dataset/clean_customer_support_tickets.csv"
df = pd.read_csv(file_path)

# 2. Combine the text columns
df["text"] = (
    df["Ticket Subject"].fillna("").astype(str)
    + " "
    + df["Ticket Description"].fillna("").astype(str)
    + " "
    + df["customer_query"].fillna("").astype(str)
)

# 3. Input and target
X = df["text"]
y = df["Ticket Type"]

# 4. Split the dataset into training and testing data
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y
)

# 5. Create the AI pipeline
model = Pipeline([
    ("tfidf", TfidfVectorizer(
        lowercase=True,
        stop_words="english"
    )),
    ("classifier", LogisticRegression(
        max_iter=1000
    ))
])

# 6. Train the model
model.fit(X_train, y_train)

# 7. Test the model
y_pred = model.predict(X_test)

# 8. Calculate accuracy
accuracy = accuracy_score(y_test, y_pred)

print("\n==============================")
print("SUPPORT PILOT - AI CLASSIFIER")
print("==============================")

print("\nNumber of training tickets:", len(X_train))
print("Number of testing tickets:", len(X_test))

print("\nAccuracy:", round(accuracy * 100, 2), "%")

print("\nClassification Report:")
print(classification_report(y_test, y_pred, zero_division=0))