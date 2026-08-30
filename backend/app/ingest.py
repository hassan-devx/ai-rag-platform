import os
import uuid
import pickle
import chromadb
from chromadb.config import Settings
from rank_bm25 import BM25Okapi
from app.pipeline import AdvancedHybridPipeline

from pathlib import Path

# Pinned to the project root directory regardless of where you run the command
from pathlib import Path
from dotenv import load_dotenv

# 1. Define ROOT_DIR relative to this file
ROOT_DIR = Path(__file__).resolve().parent.parent.parent  # Add an extra .parent if inside backend/app/

# 2. Load the .env from root
load_dotenv(ROOT_DIR / ".env")

# 3. Path for ChromaDB
DEFAULT_DB_PATH = str(ROOT_DIR / "chroma_db")
print("Root Directory:", ROOT_DIR)
print("Looking for .env at:", ROOT_DIR / ".env")
print(".env exists?:", (ROOT_DIR / ".env").exists())


class EnterpriseIngestionPipeline:
    def __init__(self, db_path=DEFAULT_DB_PATH, knowledge_base_path="./knowledge_base"):
        self.db_path = db_path
        self.knowledge_base_path = knowledge_base_path
        self.pipeline_helper = AdvancedHybridPipeline()
        
        # Initialize ChromaDB Client with telemetry disabled
        self.chroma_client = chromadb.PersistentClient(
            path=self.db_path,
            settings=Settings(anonymized_telemetry=False)
        )
        self.collection = self.chroma_client.get_or_create_collection(
            name="knowledge_base",
            metadata={"hnsw:space": "cosine"}
        )

    def extract_parent_child_chunks(self, text, parent_size=1000, child_size=250):
        """Splits data into overlapping high-context parent blocks and dense child sub-nodes."""
        words = text.split()
        documents_payload = []
        
        # Slide through text creating large parent contexts with an overlap
        for p_idx in range(0, len(words), parent_size - 150):
            parent_text = " ".join(words[p_idx:p_idx + parent_size])
            parent_id = str(uuid.uuid4())
            
            # Slice that specific parent down into highly dense semantic child chunks
            parent_words = parent_text.split()
            for c_idx in range(0, len(parent_words), child_size):
                child_text = " ".join(parent_words[c_idx:c_idx + child_size])
                if len(child_text.strip()) > 10:
                    documents_payload.append({
                        "child_id": f"child_{str(uuid.uuid4())}",
                        "parent_id": parent_id,
                        "child_text": child_text,
                        "parent_text": parent_text
                    })
        return documents_payload

    def run_sync_ingestion(self):
        print("🚀 Initializing Level 4 State-Synchronized Ingestion...")
        
        all_chunks = []
        if not os.path.exists(self.knowledge_base_path):
            os.makedirs(self.knowledge_base_path)
            print(f"📁 Created directory '{self.knowledge_base_path}'. Add your files and re-run!")
            return

        # 1. Walk through and parse knowledge files
        for filename in os.listdir(self.knowledge_base_path):
            if filename.endswith(('.txt', '.md')):
                with open(os.path.join(self.knowledge_base_path, filename), "r", encoding="utf-8") as f:
                    all_chunks.extend(self.extract_parent_child_chunks(f.read()))

        if not all_chunks:
            print("⚠️ Ingestion halted: No .txt or .md files detected in knowledge_base.")
            return

        # 2. Build Atomic Payload Arrays
        chroma_ids, chroma_embeddings, chroma_docs, chroma_metadatas = [], [], [], []
        bm25_corpus = []

        for chunk in all_chunks:
            # Construct unified metadata to map the child directly to its parent context
            metadata = {
                "parent_id": chunk["parent_id"],
                "parent_text": chunk["parent_text"],
                "child_text": chunk["child_text"]
            }
            
            # Generate vector embedding for the focused child chunk
            embedding = self.pipeline_helper.get_embedding(chunk["child_text"])
            
            chroma_ids.append(chunk["child_id"])
            chroma_embeddings.append(embedding)
            chroma_docs.append(chunk["child_text"])
            chroma_metadatas.append(metadata)
            
            # Synchronize the exact same tokenized child to BM25
            bm25_corpus.append(chunk["child_text"].lower().split(" "))

        # 3. Synchronized Transaction Commit
        print(f"📦 Committing {len(chroma_ids)} synchronized chunks to storage...")
        
        # Reset collection to ensure absolute sync consistency
        try:
            self.chroma_client.delete_collection("project_knowledge")
        except Exception:
            pass
        self.collection = self.chroma_client.get_or_create_collection(
            name="project_knowledge",
            metadata={"hnsw:space": "cosine"}
        )

        # Write to Vector Index
        self.collection.add(
            ids=chroma_ids,
            embeddings=chroma_embeddings,
            documents=chroma_docs,
            metadatas=chroma_metadatas
        )

        # Write to Sparse Index Engine and serialize state snapshot
        bm25_engine = BM25Okapi(bm25_corpus)
        with open(os.path.join(self.db_path, "bm25_state.pkl"), "wb") as f:
            pickle.dump({
                "engine": bm25_engine, 
                "docs": chroma_docs, 
                "metadatas": chroma_metadatas
            }, f)

        print(f"🎉 Level 4 Synchronization Complete! Total database records: {self.collection.count()}")

if __name__ == "__main__":
    pipeline = EnterpriseIngestionPipeline()
    pipeline.run_sync_ingestion()