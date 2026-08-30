
import os
os.environ["ANONYMIZED_TELEMETRY"] = "False"
import json
import numpy as np
import chromadb
from openai import OpenAI
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder
from chromadb.config import Settings
import pickle
from dotenv import load_dotenv
from pathlib import Path

# Safe import of database helper functions
try:
    from app.db import save_message, fetch_conversation_history
except ImportError:
    # Graceful fallback if database module is structured differently
    def save_message(session_id: str, role: str, content: str, title_hint: str = None):
        pass

    def fetch_conversation_history(session_id: str, limit: int = 10) -> list[dict]:
        return []

load_dotenv()

# Absolute path anchor ensuring ChromaDB resolves to backend/chroma_db across all entrypoints
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = str(BASE_DIR / "chroma_db")

# Universal Chroma Settings to silence telemetry errors
CHROMA_SETTINGS = Settings(anonymized_telemetry=False, is_persistent=True)


class AdvancedHybridPipeline:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "🚨 Missing Credentials: OPENAI_API_KEY environment string is not set!"
            )
            
        self.client = OpenAI(api_key=api_key)
        print("Loading BAAI/bge-reranker-base to memory CPU blocks...")
        self.reranker = CrossEncoder("BAAI/bge-reranker-base")

    def get_embedding(self, text: str) -> list[float]:
        """Generates standardized 1536-dimension vectors via OpenAI."""
        response = self.client.embeddings.create(
            model="text-embedding-3-small",
            input=[text]
        )
        return response.data[0].embedding

    def _rewrite_query_with_history(self, query: str, history: list) -> str:
        """Resolves pronouns and missing entities in follow-up queries using conversation context."""
        if not history:
            return query

        formatted_history = "\n".join(
            [f"{m.get('role', 'user')}: {m.get('content', '')}" for m in history[-4:]]
        )
        
        rewrite_prompt = (
            "Given the conversation history and a follow-up query, "
            "rewrite the follow-up query into a clear, standalone search query containing all necessary entities. "
            "Do NOT answer the question, only output the rewritten query string.\n\n"
            f"History:\n{formatted_history}\n\n"
            f"Follow-up Query: {query}\n"
            "Standalone Query:"
        )

        try:
            res = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": rewrite_prompt}],
                temperature=0.0
            )
            rewritten = res.choices[0].message.content.strip()
            return rewritten if rewritten else query
        except Exception:
            return query

    def add_to_vector_store(self, text_content: str, source: str):
        """Processes raw string text inputs directly into memory."""
        from app.parsers import file_ingestion_router
        
        chroma_client = chromadb.PersistentClient(path=DB_PATH, settings=CHROMA_SETTINGS)
        collection = chroma_client.get_or_create_collection(name="project_knowledge")
        
        chunks = file_ingestion_router(source, text_content)
        for idx, chunk_data in enumerate(chunks):
            chunk_text = chunk_data["text"]
            meta = chunk_data.get("metadata", {})
            meta["source"] = source
            meta["chunk_index"] = idx
            
            try:
                vector = self.get_embedding(chunk_text)
                collection.add(
                    embeddings=[vector],
                    documents=[chunk_text],
                    metadatas=[meta],
                    ids=[f"{source}_{idx}"]
                )
            except Exception as e:
                print(f"⚠️ Skipping fragment {idx} in {source}: {str(e)}")

    def ingest_heavy_document(self, file_path: str, file_name: str):
        """Processes massive operational manuals and textbooks from disk paths safely."""
        from app.parsers import file_ingestion_router

        chroma_client = chromadb.PersistentClient(path=DB_PATH, settings=CHROMA_SETTINGS)
        collection = chroma_client.get_or_create_collection(name="project_knowledge")

        print(f"Opening stable ingestion stream for high-capacity asset: {file_name}")
        
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            file_content = f.read()
            
        chunks = file_ingestion_router(file_name, file_content)
        
        for idx, chunk_data in enumerate(chunks):
            chunk_text = chunk_data["text"]
            meta = chunk_data["metadata"]
            meta["source"] = file_name
            meta["chunk_index"] = idx
            
            try:
                vector = self.get_embedding(chunk_text)
                collection.add(
                    embeddings=[vector],
                    documents=[chunk_text],
                    metadatas=[meta],
                    ids=[f"{file_name}_{idx}"]
                )
            except Exception as e:
                print(f"⚠️ Skipping oversized fragment index {idx} in {file_name}: {str(e)}")
                continue

        print(f"Finished indexing: {file_name}. Multi-index matrix sync operational.")

    # Compatibility Aliases
    def ingest_document(self, document_id: str, raw_text: str, metadata: dict = None):
        self.add_to_vector_store(text_content=raw_text, source=document_id)
        return {"status": "success", "document_id": document_id}

    def query_similar_context(self, query: str):
        return self.query_hybrid_context(query=query)

    def _reciprocal_rank_fusion(self, bm25_results: list[dict], vector_results: list[dict], rrf_k: int = 60) -> list[dict]:
        rrf_scores = {}
        for rank, doc in enumerate(bm25_results):
            doc_id = doc["id"]
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (rrf_k + rank + 1))
            
        for rank, doc in enumerate(vector_results):
            doc_id = doc["id"]
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (rrf_k + rank + 1))
            
        seen_ids = set()
        fused_docs = []
        all_candidates = bm25_results + vector_results
        sorted_ids = sorted(rrf_scores.items(), key=lambda item: item[1], reverse=True)
        
        for doc_id, _ in sorted_ids:
            if doc_id not in seen_ids:
                match = next((d for d in all_candidates if d["id"] == doc_id), None)
                if match:
                    fused_docs.append(match)
                    seen_ids.add(doc_id)
        return fused_docs

    def query_hybrid_context(self, query: str, stage1_top_n: int = 15, final_top_k: int = 3) -> str:
        state_file = os.path.join(DB_PATH, "bm25_state.pkl")
        
        bm25_candidates = []
        if os.path.exists(state_file):
            try:
                with open(state_file, "rb") as f:
                    bm25_snapshot = pickle.load(f)
                bm25_engine = bm25_snapshot["engine"]
                synced_docs = bm25_snapshot["docs"]
                synced_metadatas = bm25_snapshot["metadatas"]

                tokenized_query = query.lower().split(" ")
                bm25_scores = bm25_engine.get_scores(tokenized_query)
                bm25_ranked_indices = np.argsort(bm25_scores)[::-1][:stage1_top_n]
                
                bm25_candidates = [
                    {"id": f"idx_{idx}", "text": synced_docs[idx], "metadata": synced_metadatas[idx]}
                    for idx in bm25_ranked_indices if bm25_scores[idx] > 0
                ]
            except Exception as e:
                print(f"⚠️ BM25 load warning: {str(e)}")

        chroma_client = chromadb.PersistentClient(path=DB_PATH, settings=CHROMA_SETTINGS)
        collection = chroma_client.get_or_create_collection(name="project_knowledge")
        
        query_vector = self.get_embedding(query)
        vector_results = collection.query(query_embeddings=[query_vector], n_results=stage1_top_n)

        vector_candidates = []
        if vector_results and vector_results.get("documents") and vector_results["documents"][0]:
            for i in range(len(vector_results["ids"][0])):
                vector_candidates.append({
                    "id": vector_results["ids"][0][i],
                    "text": vector_results["documents"][0][i],
                    "metadata": vector_results["metadatas"][0][i]
                })

        fused_candidates = self._reciprocal_rank_fusion(bm25_candidates, vector_candidates, rrf_k=60)
        candidates_to_rerank = fused_candidates[:stage1_top_n]

        if not candidates_to_rerank:
            return ""

        evaluation_pairs = [[query, doc["text"]] for doc in candidates_to_rerank]
        rerank_scores = self.reranker.predict(evaluation_pairs)
        
        for idx, score in enumerate(rerank_scores):
            candidates_to_rerank[idx]["rerank_score"] = float(score)
            
        final_sorted_results = sorted(candidates_to_rerank, key=lambda x: x["rerank_score"], reverse=True)
        final_slices = final_sorted_results[:final_top_k]

        unique_parents = []
        for doc in final_slices:
            parent_txt = doc["metadata"].get("parent_text", doc["text"])
            if parent_txt not in unique_parents:
                unique_parents.append(parent_txt)

        return "\n\n--- CONTEXT BLOCK ---\n".join(unique_parents)

    async def generate_rag_response(
        self, 
        query: str = "", 
        session_id: str = "default_session", 
        chat_history: list = None, 
        prompt: str = None,
        **kwargs
    ):
        """Compiles deep hybrid context and conversation memory into the streaming instruction system."""
        user_query = query or prompt or ""
        
        try:
            yield f"data: {json.dumps({'text': 'X-STATUS:routing'})}\n\n"
            
            # Fetch persistent history from Postgres if not supplied in request
            if not chat_history:
                chat_history = fetch_conversation_history(session_id, limit=10)

            # Contextualize query
            contextualized_query = self._rewrite_query_with_history(user_query, chat_history)
            query_lower = contextualized_query.lower()

            local_keywords = ["local", "file", "files", "log", "logs", "project", "code", "readme", "doc", "docs", "db", "database"]
            force_local = any(k in query_lower for k in local_keywords)

            web_keywords = ["latest", "news", "current", "today", "weather", "recent", "war", "conflict", "election", "president", "who is", "what is"]
            is_live_search = False if force_local else any(k in query_lower for k in web_keywords)

            # Retrieve Context
            if is_live_search:
                yield f"data: {json.dumps({'text': 'X-STATUS:live_web_search'})}\n\n"
                from app.tools import live_web_search
                context_chunks = live_web_search(contextualized_query)
            else:
                yield f"data: {json.dumps({'text': 'X-STATUS:local_knowledge_search'})}\n\n"
                context_chunks = self.query_hybrid_context(contextualized_query, stage1_top_n=15, final_top_k=3)

            if not context_chunks or str(context_chunks).strip() in ["", "[]", "None"]:
                context_chunks = "No specific local/external context was retrieved for this prompt."

            yield f"data: {json.dumps({'text': 'X-STATUS:synthesizing'})}\n\n"

            # Save user prompt to database
            save_message(session_id=session_id, role="user", content=user_query, title_hint=user_query)

            formatted_history = "\n".join(
                [f"{m.get('role', 'user').capitalize()}: {m.get('content', '')}" for m in chat_history]
            )

            system_instruction = (
                "You are an elite, highly precise technical engineering assistant.\n"
                "You have access to the provided RETRIEVAL CONTEXT below.\n\n"
                "CRITICAL INSTRUCTIONS:\n"
                "1. If the RETRIEVAL CONTEXT contains relevant facts, use them as your primary source.\n"
                "2. If the RETRIEVAL CONTEXT lacks specific details for general knowledge queries, answer using general technical knowledge directly.\n\n"
                f"--- RETRIEVAL CONTEXT ---\n{context_chunks}\n\n"
                f"--- RECENT CONVERSATION HISTORY ---\n{formatted_history}\n"
            )

            stream = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_query}
                ],
                stream=True
            )

            assistant_accumulator = []
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    text = chunk.choices[0].delta.content
                    assistant_accumulator.append(text)
                    yield f"data: {json.dumps({'text': text})}\n\n"

            # Save assistant response to database
            full_response = "".join(assistant_accumulator)
            if full_response.strip():
                save_message(session_id=session_id, role="assistant", content=full_response)

        except Exception as e:
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'text': f'X-STATUS:error Pipeline error: {str(e)}'})}\n\n"


pipeline = AdvancedHybridPipeline()