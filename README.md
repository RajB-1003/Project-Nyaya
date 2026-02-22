# Project Nyaya 🏛️

**AI-powered voice-first legal triage assistant** for Indian citizens, focused on RTI, Domestic Violence, and Divorce law.

## Features

- 🎙️ **Voice or text input** — speak in any Indian language (Whisper transcription)
- 🤖 **Agentic form-filling** — AI extracts form fields from your voice and fills government forms for you
- 📄 **PDF generation** — produces ready-to-submit legal documents:
  - RTI Application (Section 6, RTI Act 2005)
  - DV Complaint to Protection Officer (PWDVA 2005)
  - Mutual Consent Divorce Petition (Section 13B, HMA 1955)
- 🌐 **Live government data** — fetches from official portals (CIC, IndiaCode, NALSA) before falling back to RAG
- 📚 **ChromaDB RAG** — semantic retrieval over RTI Act, PWDVA, and HMA text

## Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI, Groq Llama 3.3 70B, Whisper |
| RAG | ChromaDB, sentence-transformers |
| Web fetch | httpx, BeautifulSoup4 |
| PDF | fpdf2 |
| Frontend | Next.js 14, TypeScript, Tailwind CSS |

## Setup

### Backend
```bash
cd backend
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
# Create .env with GROQ_API_KEY=... and OPENAI_API_KEY=...
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
# Create .env.local with NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
npm run dev
```

## Usage

1. Go to `http://localhost:3000`
2. Type or speak your legal issue
3. Review the AI legal guidance
4. Click **"Generate My Filled Document"** to get a pre-filled PDF
5. Fill in any missing fields and download your document

## Disclaimer

Project Nyaya is not a law firm and does not provide legal advice. Documents generated are drafts for informational purposes only. In emergencies: **Police 100 · Women Helpline 181 · NALSA 15100**
