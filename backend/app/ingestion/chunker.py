import re
from typing import List, Dict, Any

def chunk_markdown(content: str, source_name: str, chunk_size: int = 400, overlap: int = 50) -> List[Dict[str, Any]]:
    """
    Chunks Markdown content by preserving section headers and tracking document origin.
    """
    sections = re.split(r'\n(?=#{1,3}\s)', content)
    chunks = []

    for section in sections:
        lines = section.strip().split("\n")
        if not lines or not lines[0]:
            continue
        
        header = lines[0] if lines[0].startswith("#") else "General Overview"
        body = "\n".join(lines[1:]).strip() if lines[0].startswith("#") else section.strip()
        
        words = body.split()
        if not words:
            continue

        for i in range(0, len(words), chunk_size - overlap):
            chunk_text = f"{header}\n" + " ".join(words[i:i + chunk_size])
            chunks.append({
                "text": chunk_text.strip(),
                "metadata": {
                    "source": source_name,
                    "header": header.replace("#", "").strip(),
                }
            })
            if i + chunk_size >= len(words):
                break

    return chunks