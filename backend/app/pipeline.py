import os
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from openai import OpenAI
import chromadb
from chromadb.config import Settings

load_dotenv()

# 1. Force ONNX to hide low-level hardware warning discovery logs
os.environ["ORT_LOGGING_LEVEL"] = "3" 

class RAGPipeline:
    def _init_(self):
        # Initialize OpenAI client (Keep this exactly as it was)
        self.ai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # 2. Updated Chroma Client: Keeps your environment path AND silences telemetry loops
        self.chroma_client = chromadb.PersistentClient(
            path=os.getenv("VECTOR_DB_PATH", "./chroma_db"),
            settings=Settings(
                anonymized_telemetry=False  # ◄── This kills the capture() telemetry exceptions
            )
        )
        
        # Create or fetch a collection for our vector vectors (Keep this exactly as it was)
        self.collection = self.chroma_client.get_or_create_collection(name="knowledge_base")
        
        # Text splitter (Keep this exactly as it was)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            length_function=len
        )


        
    def get_embedding(self, text: str) -> list[float]:
        """Convert raw text into a high-dimensional vector using OpenAI's embedding model."""
        response = self.ai_client.embeddings.create(
            input=[text],
            model="text-embedding-3-small"
        )
        return response.data[0].embedding

    def ingest_document(self, document_id: str, raw_text: str, metadata: dict = None):
        """Processes, chunks, embeds, and stores a document into the vector database."""
        # Step 1: Split the text into smaller semantic chunks
        chunks = self.text_splitter.split_text(raw_text)
        
        ids = []
        embeddings = []
        documents = []
        metadatas = []
        
        # Step 2: Loop through chunks and generate vector vectors
        for index, chunk in enumerate(chunks):
            chunk_id = f"{document_id}_chunk_{index}"
            embedding = self.get_embedding(chunk)
            
            ids.append(chunk_id)
            embeddings.append(embedding)
            documents.append(chunk)
            # Maintain track of metadata (like source URL or filename) for compliance/source tracking
            metadatas.append(metadata or {"source": "unknown"})
            
        # Step 3: Upsert directly into ChromaDB
        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
        return {"status": "success", "chunks_processed": len(chunks)}

    def query_similar_context(self, query: str, max_results: int = 3) -> list[str]:
        """Finds the most contextually relevant text chunks based on mathematical cosine similarity."""
        query_vector = self.get_embedding(query)
        
        results = self.collection.query(
            query_embeddings=[query_vector],
            n_results=max_results
        )
        # Flatten and return the matching text string documents
        return results['documents'][0] if results['documents'] else []


    def generate_rag_response(self, query: str):
        """Retrieves context, engineers a strict prompt, and yields a streaming LLM response."""
        # Step 1: Retrieve matching text chunks from your local DB
        context_chunks = self.query_similar_context(query, max_results=3)
        
        # Merge chunks into a single solid block of background information
        formatted_context = "\n---\n".join(context_chunks)
        
        # Step 2: System prompt engineering - establishes boundaries and forces grounding
        system_instruction = (
            "You are a precise, professional AI technical assistant.\n"
            "Answer the user's question using ONLY the provided context below. "
            "If the context does not contain the answer, state clearly that you do not possess "
            "that information based on the current knowledge base. Do not invent facts.\n\n"
            f"--- PROVIDED CONTEXT ---\n{formatted_context}"
        )

        # Step 3: Create a streaming completion request to OpenAI
        # Using stream=True returns a generator object instead of waiting for the full block
        stream = self.ai_client.chat.completions.create(
            model="gpt-4o-mini", # Snappy, cost-effective model perfect for RAG orchestration
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": query}
            ],
            stream=True
        )
        
        # Yield each text token as it arrives from the API
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content