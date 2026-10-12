# AI Risk Q\&A Bot (RAG over Telegram)

A **Retrieval-Augmented Generation (RAG)** chatbot that answers questions about **AI risk  
management** by reading a set of policy documents (PDFs). You chat with it in **Telegram**;  
it looks up the relevant passages in your documents and answers **only from them**, citing  
the source. The code and the PDFs live on a **Vultr server**, so the bot runs 24/7.

> Status: **design phase** — this README describes the structure before any code is written.

---

## What is RAG? (the short, correct version)

An LLM has a limited **context window** (its "short-term memory") — you can't paste entire  
PDFs into every question. RAG solves this:

1. **Index** the documents once (split into chunks, turn each into a numeric "embedding").
2. When a question arrives, **retrieve** the few chunks most similar to the question.
3. **Augment** the prompt with those chunks, and let the LLM **generate** an answer from them.

> Think **open-book exam**: instead of answering from memory, the LLM is handed the exact  
> pages it needs right before it answers. The documents are never memorized — they're  
> indexed and looked up on demand.

**Our grounding rule:** for AI-risk questions the LLM answers **only** from the retrieved  
chunks, **cites the source document and page**, and says **"the documents don't cover this"**  
when the answer isn't there. This keeps it honest and prevents hallucination.

---

## How information flows

```
┌────────────────────────────────────────────────────────────────────┐
│  A) INGESTION   (run once, and again whenever you add a PDF)        │
│                                                                     │
│   data/pdfs/                                                        │
│   ┌──────────┐   parse    ┌─────────┐   embed    ┌───────────────┐  │
│   │ 3 PDFs   │ ─────────▶ │ chunks  │ ─────────▶ │ vector store  │  │
│   │ (AI risk │            │ (text + │  (OpenAI   │ vectorstore   │  │
│   │ policies)│            │  page #)│  embeddings│ .json         │  │
│   └──────────┘            └─────────┘            │ (on server)   │  │
│                                                  └───────────────┘  │
└────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────┐
│  B) Q&A   (every Telegram message)                                  │
│                                                                     │
│  ┌──────────┐  question   ┌──────────────┐                          │
│  │ Telegram │ ──────────▶ │    bot.py    │                          │
│  │ chatbox  │             │  (Telegram   │                          │
│  └──────────┘             │   handler)   │                          │
│       ▲                   └──────┬───────┘                          │
│       │                          │ 1) embed the question            │
│       │                          ▼                                  │
│       │                   ┌──────────────┐   2) top-k   ┌─────────┐ │
│       │                   │ retrieval    │ ◀─────────── │ vector  │ │
│       │                   │ (cosine sim) │   chunks     │ store   │ │
│       │                   └──────┬───────┘              └─────────┘ │
│       │                          │ 3) prompt = rules + chunks + Q   │
│       │                          ▼                                  │
│       │                   ┌──────────────┐                          │
│       │                   │     LLM      │ 4) answer ONLY from the  │
│       │                   │ (gpt-4o-mini)│    chunks, cite doc+page │
│       │                   └──────┬───────┘                          │
│       │    reply                 │ 5) answer text                   │
│       └──────────────────────────┘                                  │
└────────────────────────────────────────────────────────────────────┘
```

---

## Project structure (planned)

```
ai-risk-qa-bot/
├── README.md               # this file
├── requirements.txt        # python-telegram-bot, openai, pypdf, numpy
├── .gitignore              # .env, vectorstore.json, and (optionally) PDFs
├── .env.example            # TELEGRAM_BOT_TOKEN, OPENAI_API_KEY  (template only)
├── bot.py                  # Telegram interface — entry point, runs 24/7
├── ingest.py               # one-time: PDFs -> chunks -> embeddings -> vectorstore.json
├── rag.py                  # retrieval + prompt building + LLM call
├── data/
│   ├── pdfs/               # <-- drop the 3 source PDFs here (add more later)
│   └── vectorstore.json    # generated index (chunks + embeddings)
└── deploy/
    └── ragbot.service      # systemd unit to keep bot.py running on Vultr
```

**Privacy note:** the PDFs and `vectorstore.json` live only on the server. Keep them out of  
git (`.gitignore`) unless they're meant to be public. Only code + `.env.example` are committed.

---

## How it works (step by step)

1. **Ingest** — run `python ingest.py` once. It reads every PDF in `data/pdfs/`, splits the  
   text into small chunks (keeping the page number), embeds each chunk, and saves everything  
   to `data/vectorstore.json`. Re-run this any time you add or replace a PDF.
2. **Start the bot** — `python bot.py` starts the Telegram listener (kept alive by systemd).
3. **User asks** in Telegram, e.g. *"What are the main risks of autonomous AI systems?"*
4. **Retrieve** — the bot embeds the question and finds the top-k most similar chunks from  
   the vector store (cosine similarity).
5. **Augment** — it builds a prompt: *system rules* ("answer only from the context, cite the  
   document and page, say if it's not covered") + the retrieved chunks + the question.
6. **Generate** — the LLM (`gpt-4o-mini`) writes the answer grounded in those chunks.
7. **Reply** — the bot sends the answer back to Telegram, with the source doc + page.

---

## Tech stack

| Piece         | Choice                                     | Why                                  |
| ------------- | ------------------------------------------ | ------------------------------------ |
| Interface     | **Telegram** (`python-telegram-bot`)       | Same pattern as the Telegram Planner |
| LLM (answers) | **OpenAI `gpt-4o-mini`**                   | Already set up, low cost             |
| Embeddings    | **OpenAI `text-embedding-3-small`**        | Cheap, good quality                  |
| Vector store  | **local JSON + numpy** (cosine similarity) | 3 PDFs = tiny; no external DB needed |
| PDF parsing   | **pypdf**                                  | Simple, reliable text extraction     |
| Hosting       | **Vultr VPS (Ubuntu) + systemd**           | Code + PDFs on one server, 24/7      |

> If the corpus grows large later, swap the JSON store for **FAISS** or **Chroma** — the  
> retrieval interface stays the same.

---

## Data

- **Foundation:** 3 AI-risk-management PDFs (place them in `data/pdfs/`).
- **Extending:** drop more PDFs into `data/pdfs/` and re-run `python ingest.py`. No code  
  changes needed.

---

## Deployment (Vultr)

- Server: Vultr VPS running Ubuntu; code and PDFs both live here.
- Secrets (Telegram token, OpenAI key) go in a `.env` file on the server — **never committed**.
- A `systemd` service (`deploy/ragbot.service`) keeps `bot.py` running and auto-restarts it  
  on crash/reboot.

---

## Roadmap

- [ ] `ingest.py` — PDF → chunks → embeddings → vectorstore.json
- [ ] `rag.py` — retrieval + grounded prompt + LLM answer with citations
- [ ] `bot.py` — Telegram interface
- [ ] systemd deployment on Vultr
- [ ] Add more policy PDFs
- [ ] Better chunking (overlap, headings) & page-accurate citations
- [ ] Conversation memory (follow-up questions)
- [ ] Optional: FAISS/Chroma vector store if the corpus grows
