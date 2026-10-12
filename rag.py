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
    "You are an AI risk management assistant for financial institutions. You provide "
    "information obtained from the MAS (Monetary Authority of Singapore) AI risk management "
    "materials in your corpus - the MAS Guidelines on Artificial Intelligence Risk Management "
    "and the Project MindForge handbooks, which are built on the FEAT Principles (Fairness, "
    "Ethics, Accountability, Transparency). Answer the user's question by synthesizing and "
    "summarizing information from the provided context.\n"
    "Rules:\n"
    "- Write in your own words. Do NOT copy long verbatim passages from the source.\n"
    "- Keep quotes short (under 15 words) and only when the exact wording matters.\n"
    "- Cite the source document and page number after each claim, like "
    "(MindForge Executive Handbook, p. 12).\n"
    "- If the context doesn't cover the question, say so plainly.\n"
    "- Prefer 2-4 short paragraphs. Be concise.\n"
    "- If sources disagree, note the difference."
)

# Shown when the user asks for help or the question is too unclear to answer.
# Kept short and narrow so it reads well on a phone screen.
HELP_GUIDE = (
    "AI Risk Q&A Bot\n"
    "\n"
    "Ask me anything about AI risk management from the documents I cover.\n"
    "\n"
    "Example questions:\n"
    "- What are the top AI risks for our firm?\n"
    "- How do we govern third-party AI models?\n"
    "- Summarize the AI risk appetite statement.\n"
    "\n"
    "Tips:\n"
    "- One question at a time\n"
    "- Be specific (name the doc or topic)\n"
    "- I cite the source and page number\n"
    "\n"
    "Just type your question to start."
)

HELP_KEYWORDS = (
    "help", "how do i use", "how to use", "what can you", "what do you do",
    "guide", "tutorial", "instructions", "how does this work", "commands",
    "menu", "hi", "hello", "hey",
)


def _wants_help(question: str) -> bool:
    q = question.strip().lower()
    if not q:
        return True
    if any(k in q for k in HELP_KEYWORDS):
        return True
    # Too short / vague to be a real question.
    if len(q.split()) <= 2:
        return True
    return False


def _cosine(a, b):
    a, b = np.array(a), np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


def load_store():
    with open(STORE, "r", encoding="utf-8") as f:
        return json.load(f)


def answer(question: str) -> str:
    if _wants_help(question):
        return HELP_GUIDE

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
