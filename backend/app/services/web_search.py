import os
import re
import asyncio
import httpx
from bs4 import BeautifulSoup
from ddgs import DDGS
from tavily import AsyncTavilyClient

# Initialize Tavily client using environment variables
tavily_api_key = os.getenv("TAVILY_API_KEY")
tavily_client = AsyncTavilyClient(api_key=tavily_api_key) if tavily_api_key else None


# ==========================================
# 1. TAVILY IMPLEMENTATION (Managed API)
# ==========================================
async def search_tavily(query: str, max_results: int = 2) -> str:
    """
    Executes an AI-optimized search using Tavily.
    Handles extraction, chunking, and content cleaning automatically.
    """
    if not tavily_client:
        print("⚠️ TAVILY_API_KEY missing in .env")
        return ""

    try:
        response = await tavily_client.search(
            query=query,
            topic="news", 
            search_depth="basic", 
            max_results=max_results
        )
        results = response.get("results", [])
        if not results:
            return ""

        context_blocks = []
        for idx, result in enumerate(results, 1):
            title = result.get("title", "Untitled")
            url = result.get("url", "")
            content = result.get("content", "")
            context_blocks.append(f"Source [{idx}] ({title} - {url}):\n{content}\n")

        return "\n".join(context_blocks)

    except Exception as e:
        print(f"❌ Tavily Search Error: {e}")
        return ""


# ==========================================
# 2. DUCKDUCKGO + SCRAPER IMPLEMENTATION (Manual/DIY)
# ==========================================
def clean_search_query(user_prompt: str) -> str:
    """Strips leading question words and non-alphanumeric noise."""
    query = user_prompt.lower()
    query = re.sub(r"^(has|was|is|are|did|have|what|where|who|when|why|how)\b\s*", "", query)
    query = re.sub(r'[^\w\s"]', "", query)
    cleaned = " ".join(query.split())
    return cleaned if cleaned else user_prompt


def _sync_ddg_search(keywords: str, max_results: int = 3) -> list[dict]:
    """
    Executes DuckDuckGo search. Tries news search first for timely topics,
    and falls back to text search if news returns nothing.
    """
    with DDGS() as ddgs:
        # Try DDG News Search first (returns actual recent articles & timestamps)
        try:
            news_results = list(ddgs.news(keywords, max_results=max_results))
            if news_results:
                # Standardize key names to match text search output
                return [
                    {
                        "title": r.get("title"),
                        "href": r.get("url"),
                        "body": r.get("body"),
                        "date": r.get("date")
                    }
                    for r in news_results
                ]
        except Exception as e:
            print(f"⚠️ DDG News search failed, falling back to text search: {e}")

        # Fallback to general text search
        return list(ddgs.text(keywords, max_results=max_results))


async def fetch_webpage_text(client: httpx.AsyncClient, url: str, max_chars: int = 1200) -> str:
    """Scrapes raw paragraphs from a webpage using BeautifulSoup."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    try:
        response = await client.get(url, headers=headers, timeout=4.0, follow_redirects=True)
        if response.status_code != 200:
            return ""

        soup = BeautifulSoup(response.text, "html.parser")
        for element in soup(["script", "style", "nav", "footer", "header", "form", "aside"]):
            element.decompose()

        paragraphs = [p.get_text().strip() for p in soup.find_all("p") if len(p.get_text().strip()) > 40]
        full_text = "\n".join(paragraphs)
        return full_text[:max_chars] if full_text else ""
    except Exception:
        return ""


async def search_duckduckgo(query: str, max_results: int = 2) -> str:
    """
    Manual search pipeline: cleans query, queries DDG, and scrapes top pages in parallel.
    """
    search_keywords = clean_search_query(query)
    print(f"🔍 Executing DDG Search: '{search_keywords}'")

    try:
        results = await asyncio.to_thread(_sync_ddg_search, search_keywords, max_results)
    except Exception as e:
        print(f"❌ DuckDuckGo Search Error: {e}")
        return ""

    if not results:
        return ""

    async with httpx.AsyncClient() as client:
        tasks = [fetch_webpage_text(client, result.get("href", "")) for result in results]
        page_texts = await asyncio.gather(*tasks)

    context_blocks = []
    for idx, (result, page_text) in enumerate(zip(results, page_texts), 1):
        title = result.get("title", "Untitled")
        url = result.get("href", "")
        snippet = result.get("body", "")

        content = page_text if page_text else snippet
        context_blocks.append(f"Source [{idx}] ({title} - {url}):\n{content}\n")

    return "\n".join(context_blocks)


# ==========================================
# 3. HYBRID WRAPPER (Primary & Fallback)
# ==========================================
async def execute_web_search(query: str, provider: str = "ddg") -> str:
    """
    Unified entry point for web search.
    Providers: 'ddg' (DuckDuckGo manual) or 'tavily' (Tavily AI API)
    """
    if provider == "tavily":
        context = await search_tavily(query)
        if context:
            return context
        print("⚠️ Tavily failed or empty, falling back to DuckDuckGo...")
        return await search_duckduckgo(query)
    
    # Default: DuckDuckGo first, fallback to Tavily
    context = await search_duckduckgo(query)
    if not context and tavily_client:
        print("⚠️ DuckDuckGo returned no results, falling back to Tavily...")
        return await search_tavily(query)

    return context