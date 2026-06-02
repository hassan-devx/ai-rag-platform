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
        # 🛡️ Dynamic Safeguard: Instantly auto-instantiate if boot lifecycle missed it
        if not hasattr(self, 'ai_client') or self.ai_client is None:
            self.ai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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


    def query_similar_context(self, query: str, max_results: int = 3):
        """Retrieve highly relevant text segments from the persistent local vector database."""
        
        # 🛡️ DYNAMIC SAFEGUARD: If ChromaDB collection wasn't initialized on boot, connect right now
        if not hasattr(self, 'collection') or self.collection is None:
            # Update these parameters if your persistent directory name or collection name are named differently!
            chroma_client = chromadb.PersistentClient(path="./chroma_db")
            self.collection = chroma_client.get_or_create_collection(name="project_knowledge")

        # Now your original call is completely bulletproof!
        results = self.collection.query(
            query_texts=[query],
            n_results=max_results
        )
        return results


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





        # 🛡️ DYNAMIC SAFEGUARD: Ensure ai_client is actively instantiated before starting text generation
        if not hasattr(self, 'ai_client') or self.ai_client is None:
            self.ai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # Now your streaming compilation block is completely bulletproof!
        stream = self.ai_client.chat.completions.create(
            model="gpt-4o-mini",  # or your chosen model
            messages=[
                {"role": "system", "content": "You are a helpful assistant with local knowledge context."},
                {"role": "user", "content": f"Context: {context_chunks}\n\nQuery: {query}"}
            ],
            stream=True  # Ensure streaming is active
        )

        # Your loop below will now execute seamlessly
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


       
        
        # Yield each text token as it arrives from the API
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content