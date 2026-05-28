import json
from app.pipeline import RAGPipeline
from ddgs import DDGS

pipeline = RAGPipeline()

# --- TOOL FUNCTION EXECUTIONS ---

def local_knowledge_search(query: str) -> str:
    """Searches the local persistent ChromaDB collection for data chunks."""
    chunks = pipeline.query_similar_context(query, max_results=3)
    if not chunks:
        return "No relevant local documents found."
    return "\n---\n".join(chunks)


def live_web_search(query: str) -> str:
    """Queries DuckDuckGo to pull raw, real-time current event context from the live internet."""
    # Debug print: This lets you verify in your backend terminal that the tool is actually running
    print(f"🌍 Agent is actively executing live_web_search for query: '{query}'")
    
    try:
        with DDGS() as ddgs:
            # Using ddgs.text with a timeout or fallback parameters
            results = list(ddgs.text(query, max_results=3))
            if not results:
                return "The internet search returned no active results right now."
            
            formatted_results = []
            for item in results:
                formatted_results.append(f"Title: {item['title']}\nSnippet: {item['body']}")
                
            return "\n\n---\n\n".join(formatted_results)
    except Exception as e:
        # If an IP block or connection error happens, return it explicitly so the agent knows it failed
        return f"Internet search tool error: Could not fetch live data due to connectivity limitations. Error details: {str(e)}"


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