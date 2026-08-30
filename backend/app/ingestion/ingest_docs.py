import os
import glob
from app.ingestion.chunker import chunk_markdown
from app.pipeline import AdvancedHybridPipeline

# Resolve the absolute path to knowledge_base
KNOWLEDGE_BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../knowledge_base")
)

def run_portfolio_ingestion():
    print(f"🚀 Initializing AdvancedHybridPipeline...")
    pipeline = AdvancedHybridPipeline()

    print(f"📂 Reading documents from: {KNOWLEDGE_BASE_DIR}")
    doc_paths = glob.glob(f"{KNOWLEDGE_BASE_DIR}/*.md") + glob.glob(f"{KNOWLEDGE_BASE_DIR}/*.txt")

    if not doc_paths:
        print("⚠️ No documentation found in knowledge_base directory.")
        return

    total_chunks = 0

    for file_path in doc_paths:
        file_name = os.path.basename(file_path)
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Chunk markdown while preserving hierarchy & headers
        chunks = chunk_markdown(content, source_name=file_name)
        print(f"📄 Indexing {file_name} ({len(chunks)} chunks)...")

        for chunk in chunks:
            pipeline.add_to_vector_store(
                text_content=chunk["text"],
                source=file_name
            )
            total_chunks += 1

    print(f"\n✨ Ingestion complete! Total indexed chunks: {total_chunks}")

if __name__ == "__main__":
    run_portfolio_ingestion()