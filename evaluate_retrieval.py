import pandas as pd

from rag.retriever import Retriever


# ==========================================
# RETRIEVAL EVALUATION
# ==========================================

DATASET_PATH = "dataset/helpdesk_tickets_100.csv"


def evaluate_retrieval():

    print("\n==========================================")
    print("     SUPPORTPILOT RETRIEVAL EVALUATION")
    print("==========================================\n")

    # --------------------------------------
    # LOAD TEST DATASET
    # --------------------------------------

    df = pd.read_csv(DATASET_PATH)

    retriever = Retriever()

    total_tickets = len(df)
    correct_retrievals = 0

    results = []

    print(f"Testing {total_tickets} tickets...\n")


    # --------------------------------------
    # TEST EACH TICKET
    # --------------------------------------

    for _, ticket in df.iterrows():

        description = str(
            ticket["Description"]
        )

        actual_category = str(
            ticket["Category"]
        )

        actual_subcategory = str(
            ticket["Subcategory"]
        )


        # Retrieve the best KB article

        retrieved = retriever.search(
            description,
            top_k=1
        )


        # ----------------------------------
        # CHECK RETRIEVED ARTICLE
        # ----------------------------------

        if retrieved:

            best_article = retrieved[0]

            predicted_category = str(
                best_article["category"]
            )

            predicted_subcategory = str(
                best_article["subcategory"]
            )

            score = float(
                best_article["score"]
            )

        else:

            predicted_category = ""

            predicted_subcategory = ""

            score = 0.0


        # ----------------------------------
        # COMPARE WITH ACTUAL LABEL
        # ----------------------------------

        is_correct = (
            actual_category == predicted_category
            and
            actual_subcategory == predicted_subcategory
        )


        if is_correct:

            correct_retrievals += 1


        results.append({

            "Ticket_ID": ticket["Ticket_ID"],

            "Actual_Category":
                actual_category,

            "Actual_Subcategory":
                actual_subcategory,

            "Retrieved_Category":
                predicted_category,

            "Retrieved_Subcategory":
                predicted_subcategory,

            "Score":
                round(score, 4),

            "Correct":
                is_correct

        })


    # --------------------------------------
    # CALCULATE RETRIEVAL ACCURACY
    # --------------------------------------

    retrieval_accuracy = (
        correct_retrievals /
        total_tickets
    ) * 100


    # --------------------------------------
    # DISPLAY RESULTS
    # --------------------------------------

    print("------------------------------------------")
    print("RETRIEVAL EVALUATION RESULTS")
    print("------------------------------------------")

    print(
        f"Total tickets tested : "
        f"{total_tickets}"
    )

    print(
        f"Correct retrievals   : "
        f"{correct_retrievals}"
    )

    print(
        f"Incorrect retrievals : "
        f"{total_tickets - correct_retrievals}"
    )

    print(
        f"Retrieval Accuracy   : "
        f"{retrieval_accuracy:.2f}%"
    )

    print("------------------------------------------")


    # --------------------------------------
    # SAVE DETAILED RESULTS
    # --------------------------------------

    results_df = pd.DataFrame(results)

    results_df.to_csv(
        "retrieval_evaluation_results.csv",
        index=False
    )

    print(
        "\nDetailed results saved to:"
    )

    print(
        "retrieval_evaluation_results.csv"
    )

    print(
        "\n=========================================="
    )

    print(
        "           EVALUATION COMPLETE"
    )

    print(
        "==========================================\n"
    )


# ==========================================
# RUN
# ==========================================

if __name__ == "__main__":

    evaluate_retrieval()