import os
import json
import numpy as np
import chromadb
from openai import OpenAI
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder
from chromadb.config import Settings
import pickle

class ConversationMemory:
    def __init__(self):
        self.sessions: dict[str, list[dict[str, str]]] = {}

    def add_message(self, session_id: str, role: str, content: str):
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        self.sessions[session_id].append({"role": role, "content": content})
        if len(self.sessions[session_id]) > 10:
            self.sessions[session_id] = self.sessions[session_id][-10:]

    def get_history_context(self, session_id: str) -> str:
        if session_id not in self.sessions or not self.sessions[session_id]:
            return ""
        return "\n".join([f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}" for m in self.sessions[session_id]])

chat_memory = ConversationMemory()

class AdvancedHybridPipeline:
    def __init__(self):
        # 💡 Fallback check: Read from system environment strings automatically
        api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            raise ValueError(
                "🚨 Missing Credentials: OPENAI_API_KEY environment string is not set! "
                "Please run 'export OPENAI_API_KEY=your_key' or set it up in a local .env file."
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

    # 1. Add the new router import to the top of pipeline.py
    # from app.parsers import file_ingestion_router

    def add_to_vector_store(self, text_content: str, source: str):
        """Processes raw string text inputs directly into memory."""
        from app.parsers import file_ingestion_router
        # ... your existing code here ...
        chunks = file_ingestion_router(source, text_content)
        # ... index loop logic ...

    def ingest_heavy_document(self, file_path: str, file_name: str):
        """Processes massive operational manuals and textbooks from disk paths safely."""
        from app.parsers import file_ingestion_router
        import chromadb
        
        chroma_client = chromadb.PersistentClient(path="./chroma_db")
        collection = chroma_client.get_or_create_collection(
            name="project_knowledge",
            metadata={"hnsw:space": "cosine"}
        )

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



    def _reciprocal_rank_fusion(self, bm25_results: list[dict], vector_results: list[dict], rrf_k: int = 60) -> list[dict]:
        """Fuses disparate dense/sparse score lists based strictly on candidate positions."""
        rrf_scores = {}
        
        for rank, doc in enumerate(bm25_results):
            doc_id = doc["id"]
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (rrf_k + rank + 1))
            
        for rank, doc in enumerate(vector_results):
            doc_id = doc["id"]
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (rrf_k + rank + 1))
            
        # Deduplicate and sort by high score positioning
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
        """Level 4 Hybrid Search: Evaluates pinpoint child nodes, returns full parent context arrays."""
        db_path = "./chroma_db"
        state_file = os.path.join(db_path, "bm25_state.pkl")
        
        if not os.path.exists(state_file):
            print("🚨 Synchronization Error: bm25_state.pkl missing. Run ingestion first.")
            return "System context unavailable: database index out of sync."

        # 1. Read the perfectly matched BM25 state snapshot
        with open(state_file, "rb") as f:
            bm25_snapshot = pickle.load(f)
        
        bm25_engine = bm25_snapshot["engine"]
        synced_docs = bm25_snapshot["docs"]
        synced_metadatas = bm25_snapshot["metadatas"]

        # ─── STAGE 1: SPARSE BM25 KEYWORD LOOKUP ───
        tokenized_query = query.lower().split(" ")
        bm25_scores = bm25_engine.get_scores(tokenized_query)
        bm25_ranked_indices = np.argsort(bm25_scores)[::-1][:stage1_top_n]
        
        bm25_candidates = [
            {"id": f"idx_{idx}", "text": synced_docs[idx], "metadata": synced_metadatas[idx]}
            for idx in bm25_ranked_indices if bm25_scores[idx] > 0
        ]

        # ─── STAGE 1: DENSE VECTOR LOOKUP ───
        chroma_client = chromadb.PersistentClient(
            path=db_path,
            settings=Settings(anonymized_telemetry=False)
        )
        collection = chroma_client.get_or_create_collection(name="project_knowledge")
        
        query_vector = self.get_embedding(query)
        vector_results = collection.query(query_embeddings=[query_vector], n_results=stage1_top_n)

        vector_candidates = []
        if vector_results and vector_results["documents"][0]:
            for i in range(len(vector_results["ids"][0])):
                vector_candidates.append({
                    "id": vector_results["ids"][0][i],
                    "text": vector_results["documents"][0][i],
                    "metadata": vector_results["metadatas"][0][i]
                })

        # ─── RECIPROCAL RANK FUSION (RRF) BLENDING ───
        fused_candidates = self._reciprocal_rank_fusion(bm25_candidates, vector_candidates, rrf_k=60)
        candidates_to_rerank = fused_candidates[:stage1_top_n]

        if not candidates_to_rerank:
            return ""

        # ─── STAGE 2: NEURAL CROSS-ENCODER RERANKING ───
        evaluation_pairs = [[query, doc["text"]] for doc in candidates_to_rerank]
        rerank_scores = self.reranker.predict(evaluation_pairs)
        
        for idx, score in enumerate(rerank_scores):
            candidates_to_rerank[idx]["rerank_score"] = float(score)
            
        final_sorted_results = sorted(candidates_to_rerank, key=lambda x: x["rerank_score"], reverse=True)
        final_slices = final_sorted_results[:final_top_k]

        # 💡 LEVEL 4 UPGRADE: Pull out the wide, high-context PARENT text 
        # for synthesis, entirely bypassing truncated child string sentences.
        unique_parents = []
        for doc in final_slices:
            parent_txt = doc["metadata"]["parent_text"]
            if parent_txt not in unique_parents:
                unique_parents.append(parent_txt)

        return "\n\n--- CONTEXT BLOCK ---\n".join(unique_parents)
    

    def generate_rag_response(self, query: str, session_id: str = "default_session"):
        """Compiles deep hybrid context and conversation memory into the streaming instruction system."""
        # Query our multi-stage pipeline instead of basic ChromaDB query
        context_chunks = self.query_hybrid_context(query, stage1_top_n=15, final_top_k=3)
        dialogue_history = chat_memory.get_history_context(session_id)

        system_instruction = (
            "You are an elite, highly precise technical engineering assistant. "
            "Formulate your response using the provided local vector database context. "
            "If the answer cannot be pulled from the documentation context, rely cleanly on your general technical knowledge.\n\n"
            f"--- LOCAL HYBRID RETRIEVAL CONTEXT ---\n{context_chunks}\n\n"
            f"--- RECENT CONVERSATION HISTORY ---\n{dialogue_history}\n\n"
        )

        chat_memory.add_message(session_id, "user", query)

        stream = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": query}
            ],
            stream=True
        )

        assistant_accumulator = []
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                text = chunk.choices[0].delta.content
                assistant_accumulator.append(text)
                yield f"data: {json.dumps({'text': text})}\n\n"

        chat_memory.add_message(session_id, "assistant", "".join(assistant_accumulator))

    

    def get_response(self, query: str, session_id: str = None):
        try:
            # 1. Trigger your semantic matrix search against ChromaDB
            # 2. Extract your keyword indices using BM25
            # 3. Feed the unified context chunks to your LLM generator layer
            
            # Pull your real data out of your pipeline object variables:
            real_rag_answer = self.orchestrate_rag_synthesis(query, session_id)
            
            return real_rag_answer
            
        except Exception as e:
            return f"Internal Pipeline Vector Error: {str(e)}"

# Instantiation mapping assignment for app/main.py router
pipeline = AdvancedHybridPipeline()