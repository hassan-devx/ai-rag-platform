import os
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/rag_db")

def clean_database_url(url: str):
    """Strips query parameters like '?schema=public' that break psycopg2."""
    if not url:
        return url
    
    parsed = urlparse(url)
    if not parsed.query:
        return url
    
    # Filter out unsupported parameters like 'schema'
    query_params = parse_qs(parsed.query)
    valid_psycopg2_params = {
        "sslmode", "sslrootcert", "sslcert", "sslkey",
        "connect_timeout", "application_name", "options",
        "keepalives", "keepalives_idle", "keepalives_interval", "keepalives_count"
    }
    
    filtered_query = {k: v for k, v in query_params.items() if k in valid_psycopg2_params}
    new_query = urlencode(filtered_query, doseq=True)
    
    clean_parsed = parsed._replace(query=new_query)
    return urlunparse(clean_parsed)

CLEAN_DATABASE_URL = clean_database_url(DATABASE_URL)

def get_db():
    conn = psycopg2.connect(CLEAN_DATABASE_URL, cursor_factory=RealDictCursor)
    return conn

def init_db():
    conn = get_db()
    with conn.cursor() as cur:
        # Conversations Table (Stores Titles)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                session_id VARCHAR(255) PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        # Messages Table (Stores Actual Chat Turns)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                session_id VARCHAR(255) REFERENCES conversations(session_id) ON DELETE CASCADE,
                role VARCHAR(50) NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
    conn.close()

def save_message(session_id: str, role: str, content: str, title_hint: str = None):
    try:
        conn = get_db()
        with conn.cursor() as cur:
            if title_hint and role == "user":
                cur.execute("""
                    INSERT INTO conversations (session_id, title)
                    VALUES (%s, %s)
                    ON CONFLICT (session_id) DO NOTHING;
                """, (session_id, title_hint[:50]))
            
            cur.execute("""
                INSERT INTO messages (session_id, role, content)
                VALUES (%s, %s, %s);
            """, (session_id, role, content))
            conn.commit()
        conn.close()
    except Exception as e:
        print(f"⚠️ Failed to persist message to Postgres: {str(e)}")

def fetch_conversation_history(session_id: str, limit: int = 10) -> list[dict]:
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT role, content FROM messages
                WHERE session_id = %s
                ORDER BY created_at ASC
                LIMIT %s;
            """, (session_id, limit))
            rows = cur.fetchall()
        conn.close()
        return [{"role": row["role"], "content": row["content"]} for row in rows]
    except Exception as e:
        print(f"⚠️ Failed to fetch history from Postgres: {str(e)}")
        return []


# In backend/app/db.py

def fetch_all_conversations() -> list[dict]:
    """Retrieves all chat sessions for the sidebar ordered by recent activity."""
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT session_id, title, created_at 
                FROM conversations 
                ORDER BY created_at DESC;
            """)
            rows = cur.fetchall()
        conn.close()
        return [
            {
                "session_id": row["session_id"],
                "title": row["title"],
                "created_at": str(row["created_at"])
            }
            for row in rows
        ]
    except Exception as e:
        print(f"⚠️ Failed to fetch conversations: {str(e)}")
        return []

def fetch_full_chat_history(session_id: str) -> list[dict]:
    """Retrieves the complete message history for reloading a specific chat session."""
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT role, content, created_at 
                FROM messages 
                WHERE session_id = %s 
                ORDER BY created_at ASC;
            """, (session_id,))
            rows = cur.fetchall()
        conn.close()
        return [
            {
                "role": row["role"],
                "content": row["content"],
                "created_at": str(row["created_at"])
            }
            for row in rows
        ]
    except Exception as e:
        print(f"⚠️ Failed to fetch full chat history: {str(e)}")
        return []        