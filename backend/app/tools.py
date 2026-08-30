import json
from app.pipeline import pipeline
from ddgs import DDGS

pipeline = pipeline

# --- TOOL FUNCTION EXECUTIONS ---

def local_knowledge_search(query: str) -> str:
    """
    Queries the local ChromaDB vector index using correct keyword filtering
    to avoid positional parameter parsing errors.
    """
    print(f"🔍 Executing local vector storage search for: '{query}'")
    try:
        # Assuming 'collection' is your initialized ChromaDB collection instance
        results = collection.query(
            query_texts=[query], 
            n_results=3
        )
        
        # Extract the documents text safely from the result mapping dict
        if not results or not results.get('documents') or not results['documents'][0]:
            return "No matching records found in the local database files."
            
        matched_chunks = results['documents'][0]
        return "\n\n---\n\n".join(matched_chunks)
        
    except Exception as e:
        print("🚨 ChromaDB/Local Search Crash Traceback:")
        traceback.print_exc()
        return f"Local search crashed: {str(e)}"


def live_web_search(query: str) -> str:
    """
    Queries DuckDuckGo to extract raw, real-time context from the live internet.
    Bypasses structural context managers to avoid premature client closures during SSE streaming.
    """
    print(f"🌍 Agent is actively executing live_web_search for query: '{query}'")
    
    try:
        # Instantiate the client directly rather than using a 'with' block
        ddgs = DDGS()
        results = list(ddgs.text(query, max_results=3))
        
        if not results:
            return "The live internet search returned no active results right now."
        
        formatted_results = []
        for item in results:
            formatted_results.append(f"Title: {item.get('title', 'N/A')}\nSnippet: {item.get('body', 'N/A')}")
            
        return "\n\n---\n\n".join(formatted_results)
        
    except Exception as e:
        print("🚨 DuckDuckGo/Live Search Crash Traceback:")
        traceback.print_exc()
        return f"Live search crashed: {str(e)}"


# --- OPENAI SCHEMAS DIRECTORY ---

AVAILABLE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "local_knowledge_search",
            "description": "Use this tool to search internal files for custom technical project logs or architecture updates like 'my-social-app' progress.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The specific internal project keyword or phrase."}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "live_web_search",
            "description": "Use this tool to pull current, real-time news, dates, world events, and public documentation updated after 2023.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The live public internet search keywords."} # <-- MUST MATCH FUNCTION PARAMETER
                },
                "required": ["query"], # <-- MUST MATCH FUNCTION PARAMETER
            },
        },
    }
]

# --- REACTION MAP ---
MAP_TOOLS = {
    "local_knowledge_search": local_knowledge_search,
    "live_web_search": live_web_search
}