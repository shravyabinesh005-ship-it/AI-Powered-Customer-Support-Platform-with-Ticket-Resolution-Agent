import json

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


MIN_RELEVANCE = 0.30

def normalize_query(query):

    query = query.lower()

    replacements = {
        "log out": "logout",
        "logging out": "logout",
        "logs out": "logout",
         "logged out": "logout",
        "black screen": "black screen",
        "not responding": "not responding"
    }

    for old, new in replacements.items():
        query = query.replace(old, new)

    return query


class Retriever:

    def __init__(
        self,
        knowledge_base_path="data/knowledge_base.json"
    ):

        with open(knowledge_base_path, "r") as file:
            self.documents = json.load(file)

        self.metadata_texts = []
        self.full_texts = []

        for document in self.documents:

            metadata = (
                document["category"] + " "
                + document["subcategory"] + " "
                + document["title"]
            )

            full_text = (
                metadata + " "
                + document["content"]
            )

            self.metadata_texts.append(metadata)
            self.full_texts.append(full_text)

        self.metadata_vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2)
        )

        self.metadata_vectors = (
            self.metadata_vectorizer.fit_transform(
                self.metadata_texts
            )
        )

        self.full_vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2)
        )

        self.full_vectors = (
            self.full_vectorizer.fit_transform(
                self.full_texts
            )
        )


    # ==========================================
    # KNOWLEDGE BASE SEARCH
    # ==========================================

    def search(self, query, top_k=3):
        query = normalize_query(query)

        metadata_query = (
            self.metadata_vectorizer.transform(
                [query]
            )
        )

        metadata_scores = cosine_similarity(
            metadata_query,
            self.metadata_vectors
        )[0]


        full_query = (
            self.full_vectorizer.transform(
                [query]
            )
        )

        full_scores = cosine_similarity(
            full_query,
            self.full_vectors
        )[0]


        # Base similarity score
        combined_scores = (
            0.90 * metadata_scores
            + 0.10 * full_scores
        )


        # ==========================================
        # EXACT KEYWORD / PHRASE BONUS
        # ==========================================

        query_words = set(
            query.lower().split()
        )


        for index, document in enumerate(
            self.documents
        ):

            important_text = (
                document["subcategory"]
                + " "
                + document["title"]
            ).lower()


            important_words = set(
                important_text.split()
            )


            # Count important words from the
            # user's query that occur in the
            # subcategory/title.

            matching_words = (
                query_words & important_words
            )


            if matching_words:

                bonus = (
                    len(matching_words)
                    / max(len(query_words), 1)
                )


                combined_scores[index] += (
                    0.30 * bonus
                )


            # Give an additional bonus when the
            # complete query phrase appears.

            if query.lower() in important_text:

                combined_scores[index] += 0.50


        # ==========================================
        # RANK RESULTS
        # ==========================================

        ranked_indices = (
            combined_scores.argsort()[::-1]
        )


        results = []


        for index in ranked_indices:

            score = float(
                combined_scores[index]
            )


            if score < MIN_RELEVANCE:
                continue


            document = self.documents[index]


            results.append({

                "id": document["id"],

                "category": document["category"],

                "subcategory": document["subcategory"],

                "priority": document["priority"],

                "title": document["title"],

                "content": document["content"],

                "score": score

            })


            if len(results) >= top_k:
                break


        return results


# ==========================================
# TEST RETRIEVER
# ==========================================

if __name__ == "__main__":

    retriever = Retriever()


    test_queries = [

        "My laptop screen is completely black",

        "My application crashes when I log out",

        "I cannot access the system because of conditional access"

    ]


    print("\n==========================================")
    print("       SUPPORTPILOT RETRIEVER TEST")
    print("==========================================")


    for query in test_queries:

        print("\n------------------------------------------")

        print("Query:")
        print(query)


        results = retriever.search(
            query,
            top_k=3
        )


        if not results:

            print(
                "\nNo sufficiently relevant "
                "knowledge-base articles found."
            )

            continue


        print("\nRelevant Knowledge Articles:")


        for result in results:

            print(
                f"- {result['title']} "
                f"(Score: {result['score']:.4f})"
            )