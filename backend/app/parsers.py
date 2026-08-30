import ast
import json
from marko import Markdown

def chunk_plain_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[dict]:
    """Fallback chunker that splits text smoothly by words without cutting words in half."""
    words = text.split()
    chunks = []
    start = 0
    
    while start < len(words):
        end = start + chunk_size
        chunk_words = words[start:end]
        chunks.append({
            "text": " ".join(chunk_words),
            "metadata": {"type": "plain_text"}
        })
        start += chunk_size - overlap
        if end >= len(words):
            break
            
    return chunks

def chunk_markdown(text: str) -> list[dict]:
    """Splits markdown files logically by sections using headers (#, ##, ###)."""
    lines = text.split("\n")
    chunks = []
    current_header = "Introduction"
    current_section = []
    
    for line in lines:
        if line.startswith("#"):
            if current_section:
                chunks.append({
                    "text": f"Section: {current_header}\n" + "\n".join(current_section),
                    "metadata": {"type": "markdown", "header": current_header}
                })
                current_section = []
            current_header = line.lstrip("#").strip()
        else:
            current_section.append(line)
            
    if current_section:
        chunks.append({
            "text": f"Section: {current_header}\n" + "\n".join(current_section),
            "metadata": {"type": "markdown", "header": current_header}
        })
        
    return chunks

def chunk_python_code(code: str) -> list[dict]:
    """Uses Abstract Syntax Trees to break Python scripts into complete functions/classes."""
    chunks = []
    try:
        tree = ast.parse(code)
        lines = code.split("\n")
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                start_line = node.lineno - 1
                end_line = node.end_lineno
                block_content = "\n".join(lines[start_line:end_line])
                
                chunks.append({
                    "text": f"Code Block ({node.name}):\n{block_content}",
                    "metadata": {
                        "type": "code_structure",
                        "name": node.name,
                        "start_line": node.lineno,
                        "end_line": node.end_lineno
                    }
                })
    except Exception:
        # Fallback to plain text split if code has syntax errors or isn't compilable
        return chunk_plain_text(code, chunk_size=400)
        
    return chunks if chunks else chunk_plain_text(code, chunk_size=400)



def chunk_large_textbook(text: str, max_tokens: int = 1000) -> list[dict]:
    """
    Slices ultra-heavy raw text strings into strict, safely bounded 
    semantic paragraph blocks to ensure OpenAI context windows never error out.
    """
    # Split by double newlines to preserve natural paragraph structure
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = []
    current_word_count = 0
    
    for para in paragraphs:
        para_words = para.split()
        if not para_words:
            continue
            
        # Rough estimation: 1 word ~ 1.3 tokens
        if current_word_count + len(para_words) > max_tokens:
            if current_chunk:
                chunks.append({
                    "text": "\n\n".join(current_chunk),
                    "metadata": {"type": "textbook_section"}
                })
            current_chunk = [para]
            current_word_count = len(para_words)
        else:
            current_chunk.append(para)
            current_word_count += len(para_words)
            
    if current_chunk:
        chunks.append({
            "text": "\n\n".join(current_chunk),
            "metadata": {"type": "textbook_section"}
        })
        
    return chunks

# Now update your main router inside parsers.py to support a textbook/doc format!
def file_ingestion_router(file_name: str, file_content: str) -> list[dict]:
    """Routes files based on extension to extract context-rich text chunks."""
    ext = file_name.split(".")[-1].lower()
    
    if ext == "py":
        return chunk_python_code(file_content)
    elif ext in ["md", "markdown"]:
        return chunk_markdown(file_content)
    elif ext in ["pdf", "txt", "doc"] and len(file_content) > 50000:
        # 💡 If it's a massive text document or manual, route it to the textbook chunker
        return chunk_large_textbook(file_content)
    else:
        return chunk_plain_text(file_content)