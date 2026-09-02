import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, classification_report


# ==========================================
# 1. LOAD THE DATASET
# ==========================================

file_path = "dataset/helpdesk_tickets.csv"

df = pd.read_csv(file_path)

print("\n===================================")
print("SUPPORT PILOT - IT TICKET CLASSIFIER")
print("===================================")

print("\nTotal tickets in dataset:", len(df))


# ==========================================
# 2. TAKE A BALANCED SAMPLE
# ==========================================

# We don't need all 1 million tickets.
# We take 1,000 tickets from each category.

sample_size = 1000

df_sample = (
    df.groupby("Category", group_keys=False)
      .sample(n=sample_size, random_state=42)
      .reset_index(drop=True)
)

print("\nTickets used for training:", len(df_sample))

print("\nCategory distribution:")
print(df_sample["Category"].value_counts())


# ==========================================
# 3. CLEAN THE TEXT
# ==========================================

df_sample["Description"] = (
    df_sample["Description"]
    .fillna("")
    .astype(str)
    .str.lower()
)

X = df_sample["Description"]
y = df_sample["Category"]


# ==========================================
# 4. SPLIT INTO TRAINING AND TESTING DATA
# ==========================================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y
)

print("\nTraining tickets:", len(X_train))
print("Testing tickets:", len(X_test))


# ==========================================
# 5. CREATE THE AI MODEL
# ==========================================

model = Pipeline([
    (
        "tfidf",
        TfidfVectorizer(
            stop_words="english",
            max_features=5000
        )
    ),
    (
        "classifier",
        LogisticRegression(
            max_iter=1000
        )
    )
])


# ==========================================
# 6. TRAIN THE MODEL
# ==========================================

print("\nTraining the AI model...")

model.fit(X_train, y_train)
import joblib

joblib.dump(model, "ticket_classifier.joblib")

print("Model saved as ticket_classifier.joblib")

print("Training completed!")




# ==========================================
# 7. TEST THE MODEL
# ==========================================

y_pred = model.predict(X_test)

accuracy = accuracy_score(y_test, y_pred)


# ==========================================
# 8. DISPLAY RESULTS
# ==========================================

print("\n===================================")
print("MODEL RESULTS")
print("===================================")

print("\nAccuracy:", round(accuracy * 100, 2), "%")

print("\nClassification Report:")
print(classification_report(
    y_test,
    y_pred,
    zero_division=0
))


# ==========================================
# 9. TEST WITH A NEW TICKET
# ==========================================

new_ticket = [
    "I cannot connect to the company network and my internet connection keeps failing"
]

prediction = model.predict(new_ticket)

print("\n===================================")
print("TEST TICKET")
print("===================================")

print("\nTicket:")
print(new_ticket[0])

print("\nPredicted Category:")
print(prediction[0])