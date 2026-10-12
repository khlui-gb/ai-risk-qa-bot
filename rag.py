import os, json
import numpy as np
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")
CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-5-nano")
TOP_K = int(os.getenv("TOP_K", "4"))
STORE = "data/vectorstore.json"

SYSTEM_PROMPT = (
    "You are an assistant that answers questions about AI risk management "
    "STRICTLY using the provided context passages. Rules:\n"
    "1. Answer ONLY from the context. Do not use outside knowledge.\n"
    "2. Cite the source document name and page number for every claim.\n"
    "3. If the context does not cover the question, say exactly: "
    "'The provided documents do not cover this.'\n"
    "4. Be concise and factual."
)


def _cosine(a, b):
    a, b = np.array(a), np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


def load_store():
    with open(STORE, "r", encoding="utf-8") as f:
        return json.load(f)


def answer(question: str) -> str:
    store = load_store()
    chunks = store["chunks"]

    q_emb = client.embeddings.create(model=EMBED_MODEL, input=[question]).data[0].embedding
    scored = [(c, _cosine(q_emb, c["embedding"])) for c in chunks]
    scored.sort(key=lambda x: x[1], reverse=True)
    top = scored[:TOP_K]

    context = "\n\n".join(
        f"[Source: {c['source']}, page {c['page']}]\n{c['text']}" for c, _ in top
    )
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"},
    ]
    resp = client.chat.completions.create(
        model=CHAT_MODEL, messages=messages, temperature=0.2
    )
    return resp.choices[0].message.content


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) or "What are the main risks of autonomous AI systems?"
    print(answer(q))
