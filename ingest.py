import os, glob, json
import numpy as np
from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")

PDF_DIR = "data/pdfs"
OUT = "data/vectorstore.json"
CHUNK_CHARS = 1000
OVERLAP = 150


def extract_pages(path):
    """Return list of (page_number, text) for one PDF."""
    reader = PdfReader(path)
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        pages.append((i, text))
    return pages


def chunk_text(text, page_no, source):
    """Split a page into overlapping chunks, keeping page + source."""
    chunks = []
    start = 0
    while start < len(text):
        piece = text[start:start + CHUNK_CHARS]
        if piece.strip():
            chunks.append({
                "text": piece.strip(),
                "page": page_no,
                "source": source,
            })
        start += CHUNK_CHARS - OVERLAP
    return chunks


def embed(texts):
    resp = client.embeddings.create(model=EMBED_MODEL, input=texts)
    return [d.embedding for d in resp.data]


def main():
    records = []
    for pdf_path in glob.glob(os.path.join(PDF_DIR, "*.pdf")):
        source = os.path.basename(pdf_path)
        print(f"Ingesting {source} ...")
        for page_no, text in extract_pages(pdf_path):
            records.extend(chunk_text(text, page_no, source))

    print(f"Embedding {len(records)} chunks ...")
    texts = [r["text"] for r in records]
    # embed in batches to stay within API limits
    embeddings = []
    for i in range(0, len(texts), 100):
        embeddings.extend(embed(texts[i:i + 100]))

    for r, e in zip(records, embeddings):
        r["embedding"] = e

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"model": EMBED_MODEL, "chunks": records}, f, ensure_ascii=False)
    print(f"Saved {len(records)} chunks -> {OUT}")


if __name__ == "__main__":
    main()
