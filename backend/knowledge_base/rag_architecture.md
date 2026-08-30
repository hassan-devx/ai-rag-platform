# Hybrid RAG & Contextual Synthesis Platform

## Core Technologies
The platform is built with Next.js 14, Tailwind CSS, PostgreSQL, Prisma ORM, FastAPI, ChromaDB, BM25Okapi, and OpenAI text-embedding-3-small with GPT-4o-mini.

## Retrieval Strategy
1. Multi-turn query contextualization: Rewrites conversational references into standalone search queries.
2. Dual-channel retrieval: Queries 15 candidates from ChromaDB (dense vector) and 15 candidates from BM25 (sparse lexical).
3. Reciprocal Rank Fusion (RRF): Combines dense and sparse ranks using k=60.
4. Cross-Encoder Reranking: Uses BAAI/bge-reranker-base to score top-3 authoritative context chunks.
5. Streaming Synthesis: Delivers tokens via FastAPI Server-Sent Events (SSE).