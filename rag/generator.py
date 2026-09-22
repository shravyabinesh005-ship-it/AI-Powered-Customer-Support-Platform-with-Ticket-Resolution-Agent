import os

from dotenv import load_dotenv
from google import genai

from rag.retriever import Retriever


# =========================================================
# LOAD ENVIRONMENT VARIABLES
# =========================================================

load_dotenv()


# =========================================================
# RESOLUTION GENERATOR
# =========================================================

class ResolutionGenerator:

    def __init__(self):

        api_key = os.getenv(
            "GEMINI_API_KEY"
        )

        if not api_key:

            raise ValueError(
                "GEMINI_API_KEY was not found. "
                "Please check your .env file."
            )

        self.client = genai.Client(
            api_key=api_key
        )

        self.retriever = Retriever()

        self.model_name = (
            "gemini-3.6-flash"
        )

    # =====================================================
    # 1. TICKET ANALYSIS & QUERY GENERATION
    # =====================================================

    def generate_search_query(
        self,
        ticket_description
    ):

        # For the current milestone, the ticket description
        # itself is converted into a clean retrieval query.

        query = ticket_description.strip()

        return query

    # =====================================================
    # 2. CONTEXT AUGMENTATION
    # =====================================================

    def build_context(
        self,
        results
    ):

        context_parts = []

        for result in results:

            context_parts.append(
                f"""
Knowledge Base ID: {result['id']}
Title: {result['title']}
Category: {result['category']}
Subcategory: {result['subcategory']}
Relevance Score: {result['score']:.4f}

Content:
{result['content']}
"""
            )

        return "\n".join(
            context_parts
        )

    # =====================================================
    # FALLBACK RESPONSE
    # =====================================================

    def build_fallback_resolution(
        self,
        reason,
        search_query,
        sources,
        context
    ):

        return {

            "resolution": (
                "The AI resolution service is temporarily "
                "unavailable. The ticket has been analyzed "
                "and relevant knowledge-base information "
                "was retrieved, but an AI-generated "
                "resolution could not be completed. "
                "Additional investigation is required."
            ),

            "sources": sources,

            "query": search_query,

            "context": context,

            "workflow": {

                "ticket_analysis": {

                    "status": "completed",

                    "message":
                        "Ticket analyzed and retrieval "
                        "query generated.",

                    "query":
                        search_query

                },

                "knowledge_retrieval": {

                    "status":
                        "completed",

                    "message":
                        (
                            f"{len(sources)} relevant "
                            "knowledge-base article(s) "
                            "retrieved."
                        ),

                    "articles_found":
                        len(sources),

                    "sources":
                        sources

                },

                "context_augmentation": {

                    "status":
                        "completed",

                    "message":
                        (
                            f"Retrieved knowledge from "
                            f"{len(sources)} article(s) "
                            "added to the AI context."
                        ),

                    "context_documents":
                        len(sources)

                },

                "resolution_generation": {

                    "status":
                        "failed_with_fallback",

                    "message":
                        (
                            "Gemini resolution generation "
                            "was temporarily unavailable. "
                            "Fallback response returned."
                        ),

                    "model":
                        self.model_name,

                    "error":
                        str(reason)

                }

            }

        }

    # =====================================================
    # 3. RESOLUTION GENERATION
    # =====================================================

    def generate_resolution(
        self,
        ticket_description
    ):

        # --------------------------------------
        # STEP 1: TICKET ANALYSIS & QUERY
        # --------------------------------------

        search_query = (
            self.generate_search_query(
                ticket_description
            )
        )

        # --------------------------------------
        # STEP 2: KNOWLEDGE BASE RETRIEVAL
        # --------------------------------------

        results = self.retriever.search(
            search_query,
            top_k=3
        )

        # --------------------------------------
        # HANDLE NO RETRIEVAL RESULTS
        # --------------------------------------

        if not results:

            return {

                "resolution": (

                    "Insufficient knowledge-base "
                    "information was found to generate "
                    "a reliable resolution. Additional "
                    "investigation is required."

                ),

                "sources": [],

                "query": search_query,

                "context": "",

                "workflow": {

                    "ticket_analysis": {

                        "status":
                            "completed",

                        "message":
                            (
                                "Ticket analyzed and "
                                "retrieval query generated."
                            )

                    },

                    "knowledge_retrieval": {

                        "status":
                            "insufficient",

                        "message":
                            (
                                "No sufficiently relevant "
                                "knowledge-base articles "
                                "were found."
                            ),

                        "articles_found":
                            0

                    },

                    "context_augmentation": {

                        "status":
                            "insufficient",

                        "message":
                            (
                                "Context could not be "
                                "created because no "
                                "relevant articles were "
                                "retrieved."
                            )

                    },

                    "resolution_generation": {

                        "status":
                            "completed_with_warning",

                        "message":
                            (
                                "Resolution could not "
                                "be reliably generated "
                                "from the knowledge base."
                            ),

                        "model":
                            self.model_name

                    }

                }

            }

        # --------------------------------------
        # STEP 3: CONTEXT AUGMENTATION
        # --------------------------------------

        context = self.build_context(
            results
        )

        # --------------------------------------
        # STORE SOURCE INFORMATION
        # --------------------------------------

        sources = []

        for result in results:

            sources.append({

                "id":
                    result["id"],

                "title":
                    result["title"],

                "category":
                    result["category"],

                "subcategory":
                    result["subcategory"],

                "score":
                    round(
                        result["score"],
                        4
                    )

            })

        # --------------------------------------
        # STEP 4: CREATE GEMINI PROMPT
        # --------------------------------------

        prompt = f"""
You are an enterprise IT support resolution assistant.

Generate a troubleshooting resolution for the support ticket
using ONLY the enterprise knowledge-base information provided
below as your primary source.

IMPORTANT RULES:

1. Use the provided knowledge base as the primary source.
2. Do not invent company-specific policies or procedures.
3. Do not claim that something was performed if it was not.
4. Provide clear numbered troubleshooting steps.
5. Explain the likely cause when the knowledge base supports it.
6. If the knowledge base is insufficient, clearly say that
   additional investigation is required.
7. Keep the response concise and professional.
8. Mention the Knowledge Base ID used for the resolution.
9. Do not cite knowledge articles that were not provided.

SUPPORT TICKET:
{ticket_description}

RETRIEVAL QUERY:
{search_query}

ENTERPRISE KNOWLEDGE BASE:
{context}

Format your response exactly with these sections:

### Likely Cause
Explain the likely cause based on the knowledge base.

### Troubleshooting Steps
Provide numbered troubleshooting steps.

### Recommended Resolution
Explain what the support agent should recommend.

### Knowledge Base Source
Mention the relevant Knowledge Base ID and article title.
"""

        # =================================================
        # STEP 5: GEMINI GENERATION
        # =================================================

        try:

            response = (
                self.client.models.generate_content(

                    model=self.model_name,

                    contents=prompt

                )
            )

            # ------------------------------------------
            # CHECK GEMINI RESPONSE
            # ------------------------------------------

            if not response:

                raise RuntimeError(
                    "Gemini returned an empty response."
                )

            resolution = (
                response.text
                if response.text
                else ""
            )

            resolution = resolution.strip()

            if not resolution:

                raise RuntimeError(
                    "Gemini returned an empty resolution."
                )

        except Exception as error:

            # ------------------------------------------
            # GEMINI FAILURE
            # ------------------------------------------

            print(
                "\n=========================================="
            )

            print(
                "GEMINI RESOLUTION GENERATION ERROR"
            )

            print(
                "=========================================="
            )

            print(
                error
            )

            print(
                "Using fallback resolution."
            )

            print(
                "==========================================\n"
            )

            return self.build_fallback_resolution(

                reason=error,

                search_query=search_query,

                sources=sources,

                context=context

            )

        # =================================================
        # STEP 6: COMPLETE WORKFLOW INFORMATION
        # =================================================

        workflow = {

            "ticket_analysis": {

                "status":
                    "completed",

                "message":
                    (
                        "Ticket analyzed and "
                        "retrieval query generated."
                    ),

                "query":
                    search_query

            },

            "knowledge_retrieval": {

                "status":
                    "completed",

                "message":
                    (
                        f"{len(results)} relevant "
                        "knowledge-base article(s) "
                        "retrieved."
                    ),

                "articles_found":
                    len(results),

                "sources":
                    sources

            },

            "context_augmentation": {

                "status":
                    "completed",

                "message":
                    (
                        f"Retrieved knowledge from "
                        f"{len(results)} article(s) "
                        "added to the Gemini context."
                    ),

                "context_documents":
                    len(results)

            },

            "resolution_generation": {

                "status":
                    "completed",

                "message":
                    (
                        "Gemini generated the "
                        "troubleshooting resolution."
                    ),

                "model":
                    self.model_name

            }

        }

        # =================================================
        # STEP 7: RETURN COMPLETE RESULT
        # =================================================

        return {

            "resolution":
                resolution,

            "sources":
                sources,

            "query":
                search_query,

            "context":
                context,

            "workflow":
                workflow

        }


# =========================================================
# TEST THE RAG PIPELINE
# =========================================================

if __name__ == "__main__":

    generator = ResolutionGenerator()

    test_ticket = (
        "My computer cannot connect to the office network."
    )

    print(
        "\n=========================================="
    )

    print(
        "      SUPPORTPILOT RAG PIPELINE TEST"
    )

    print(
        "=========================================="
    )

    print(
        "\n[1] Ticket Analysis & Query Generation"
    )

    result = generator.generate_resolution(
        test_ticket
    )

    print(
        "\nGenerated Query:"
    )

    print(
        result["query"]
    )

    print(
        "\n[2] Knowledge Base Retrieval"
    )

    for source in result["sources"]:

        print(
            f"- {source['title']} "
            f"(Score: {source['score']})"
        )

    print(
        "\n[3] Context Augmentation"
    )

    print(
        f"Context documents: "
        f"{result['workflow']['context_augmentation'].get('context_documents', 0)}"
    )

    print(
        "\n[4] Gemini Resolution Generation"
    )

    print(
        result["resolution"]
    )

    print(
        "\n=========================================="
    )

    print(
        "              WORKFLOW STATUS"
    )

    print(
        "=========================================="
    )

    for stage, details in result["workflow"].items():

        print(
            f"{stage}: "
            f"{details['status']}"
        )