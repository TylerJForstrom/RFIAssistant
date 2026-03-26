# Smart RFI Assistant

An AI-powered construction workflow tool that retrieves similar historical RFIs and generates grounded draft responses using hybrid semantic search and optional LLM generation.

## Features

- Upload and search historical RFI datasets
- Upload PDFs and convert extracted content into chunked searchable rows
- Page-level PDF source citations
- Hybrid retrieval using:
  - word-level TF-IDF
  - character-level TF-IDF
  - latent semantic analysis (SVD)
  - FAISS vector search over semantic document vectors
  - local reranking over retrieved candidates
  - optional OpenAI embeddings
- Persistent FAISS index cached on disk
- Filter by trade, project, and spec section
- Duplicate RFI detection
- Confidence scoring
- Match explanations
- Safeguards for weak context
- Structured draft generation
- Feedback loop with accept / edit / reject
- Reviewed drafts saved to SQLite
- Approved drafts can be synced back into the searchable dataset
- Streamlit UI for review and demo

## Current Retrieval Stack

- lexical retrieval with TF-IDF
- character-level phrase matching
- semantic retrieval with SVD
- FAISS nearest-neighbor search on semantic vectors
- reranking over the top candidate set
- chunk-based PDF ingestion
- page-level PDF citations
- optional LLM-assisted drafting
