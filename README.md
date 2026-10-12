# AI Risk Q&A Bot (RAG over Telegram)

A Retrieval-Augmented Generation (RAG) chatbot that answers questions about **AI risk
management** from a set of policy PDFs. You chat with it in **Telegram**; it looks up the
relevant passages and answers **only from them**, citing the source document + page.

## Corpus (in `data/pdfs/`, git-ignored)

- `Guidelines on Artificial Intelligence Risk Management.pdf`
- `MindForge AI Risk Management Executive Handbook.pdf`
- `MindForge AI Risk Management Operationalisation Handbook.pdf`

## Stack

- **Telegram** (`python-telegram-bot`) — chat interface
- **OpenAI `gpt-5-nano`** — answers
- **OpenAI `text-embedding-3-small`** — embeddings
- **Local JSON + numpy** — cosine-similarity vector store (corpus is tiny)
- **pypdf** — PDF text extraction
- **Vultr VPS (Ubuntu) + systemd** — 24/7 hosting

## Setup (local)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # fill in TELEGRAM_BOT_TOKEN + OPENAI_API_KEY
python ingest.py             # PDFs -> data/vectorstore.json (run on PDF change)
```

## Run

```bash
python rag.py "your question"   # test retrieval + answer
python bot.py                   # start the Telegram listener (Ctrl+C to stop)
```

## Deploy to Vultr (24/7)

See `ai-risk-qa-bot-implementation-guide.md` (Step 10–11): push to GitHub, clone on the
server, `pip install`, upload the PDFs, `python ingest.py`, then install
`deploy/ragbot.service` via systemd so the bot auto-restarts.

## Privacy

PDFs and `vectorstore.json` live only on the server / local machine and are git-ignored.
Only code and `.env.example` are committed.
