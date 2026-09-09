# SupportPilot – Milestone 2 Test Report

## Milestone 2: Knowledge Retrieval & Resolution Generation

### Objective

The objective of Milestone 2 is to implement a Retrieval-Augmented Generation (RAG)
workflow that retrieves relevant enterprise knowledge-base articles and uses the
retrieved information to generate troubleshooting resolutions.

---

## RAG Workflow

The implemented workflow is:

Ticket
   ↓
Ticket Analysis & Query Generation
   ↓
Knowledge Base Retrieval
   ↓
Context Augmentation
   ↓
Gemini Resolution Generation
   ↓
Final Troubleshooting Resolution

---

## Technologies Used

- Python
- Flask
- TF-IDF Vectorization
- Cosine Similarity
- JSON Knowledge Base
- Google Gemini
- HTML
- CSS
- JavaScript
- SQLite

---

## Knowledge Retrieval

The system uses TF-IDF and cosine similarity to retrieve relevant
knowledge-base articles.

The retriever considers:

- Category
- Subcategory
- Article title
- Troubleshooting content

Query normalization is also used to handle common variations such as:

- "log out" → "logout"
- "logging out" → "logout"
- "logged out" → "logout"

The system returns the top relevant knowledge-base articles based on
their similarity scores.

---

## Context Augmentation

The retrieved knowledge-base articles are formatted into a context
containing:

- Knowledge Base ID
- Article title
- Category
- Subcategory
- Relevance score
- Troubleshooting content

This context is provided to Gemini for resolution generation.

---

## Resolution Generation

Google Gemini generates the final troubleshooting resolution using
the retrieved knowledge-base context.

The generated response contains:

- Likely Cause
- Troubleshooting Steps
- Recommended Resolution
- Knowledge Base Source

The system is instructed to avoid inventing company-specific information
when the knowledge base does not provide sufficient information.

---

# Evaluation Results

## Test Case 1 – Laptop Screen

### Input

"My laptop screen is completely black."

### Retrieved Article

Laptop screen black screen Troubleshooting Guide

### Result

Correct knowledge-base article retrieved.

### Status

PASS

---

## Test Case 2 – Application Crash

### Input

"My application crashes whenever I log out."

### Retrieved Article

Application crash on logout Troubleshooting Guide

### Result

Correct knowledge-base article retrieved after query normalization.

### Status

PASS

---

## Test Case 3 – Conditional Access

### Input

"I cannot access the system because of conditional access."

### Retrieved Article

Access denied by conditional access Troubleshooting Guide

### Result

Correct knowledge-base article retrieved.

### Status

PASS

---

## Test Case 4 – Unknown Knowledge

### Input

"My laptop camera is physically damaged and the lens is broken."

### Retrieved Article

Laptop screen hinge broken Troubleshooting Guide

### Result

The retrieved article was related to physical laptop damage but did not
provide camera-specific troubleshooting information.

The generated resolution correctly stated that the knowledge base was
insufficient for camera repair and recommended additional hardware
investigation.

### Status

PASS

---

# Overall Result

The Milestone 2 RAG pipeline successfully performs:

1. Ticket analysis
2. Query generation
3. Knowledge-base retrieval
4. Context augmentation
5. AI resolution generation
6. Knowledge-source presentation
7. Insufficient-knowledge handling

The implemented system successfully connects ticket information with
enterprise knowledge and generates grounded troubleshooting responses.ok