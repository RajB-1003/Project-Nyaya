# Project Nyaya — Technical Documentation

> **Voice-first AI legal triage for marginalized communities in India**
> Covers RTI (Right to Information), Domestic Violence (PWDVA), and Mutual Consent Divorce (HMA).

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture](#2-architecture)
3. [Tech Stack](#3-tech-stack)
4. [Project Structure](#4-project-structure)
5. [Setup & Installation](#5-setup--installation)
6. [Environment Variables](#6-environment-variables)
7. [Backend API Reference](#7-backend-api-reference)
8. [Frontend Components](#8-frontend-components)
9. [Context Retrieval Pipeline](#9-context-retrieval-pipeline)
10. [Agentic Form Filling](#10-agentic-form-filling)
11. [PDF Generation](#11-pdf-generation)
12. [Legal Knowledge Base](#12-legal-knowledge-base)
13. [Deployment](#13-deployment)
14. [Disclaimer](#14-disclaimer)

---

## 1. Project Overview

Project Nyaya is a web application that helps underprivileged Indian citizens understand their legal rights and take action. A user speaks or types their legal situation in any Indian language — the AI analyses it, identifies the legal category (RTI / Domestic Violence / Divorce), explains their rights with specific act citations, and then offers to fill the relevant government form and generate a ready-to-submit PDF draft.

### Key Capabilities

| Capability | Description |
|---|---|
| **Multilingual input** | Browser-native Web Speech API — Hindi, Tamil, Telugu, Kannada, Malayalam, Marathi, Bengali, Gujarati, Punjabi, Urdu, English |
| **Legal analysis** | Groq Llama 3.3 70B with RAG context — cites specific sections, timelines, fees, authorities |
| **Live gov data** | Fetches from CIC, IndiaCode, NALSA, Nyaaya, WCD portals before falling back to RAG |
| **Agentic form filling** | Extracts field data from voice, pre-fills forms, asks for missing info |
| **PDF generation** | Produces government-style RTI Application, DV Complaint, Divorce Petition drafts |

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Browser (Next.js)                       │
│                                                              │
│  [Language Selector] → [Mic / Text Input]                    │
│         │                                                    │
│  webkitSpeechRecognition (browser-native, no backend needed) │
│         │                                                    │
│  [POST /api/analyze] ──────────────────────────────────────► │
└───────────────────────────────┬─────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend (Python)                   │
│                                                              │
│  1. Web Fetcher ──► Official Gov Portals (httpx, 6s timeout) │
│       │  (fails/short?)                                      │
│       ▼                                                      │
│  2. ChromaDB RAG ─► ONNXMiniLM-L6-v2 embeddings             │
│       │             RTI Act / PWDVA / HMA chunks             │
│       ▼                                                      │
│  3. Groq Llama 3.3 70B ─► Structured JSON response          │
│                                                              │
│  → /api/extract_form  (field extraction from voice text)     │
│  → /api/generate_form_pdf  (fpdf2 PDF builder)               │
└─────────────────────────────────────────────────────────────┘
                                │
                                ▼
                    /static/<uuid>.pdf  (served as static file)
```

### Context Retrieval Priority

```
User text
    │
    ├─► [1] Live web fetch from government portals  (6s timeout)
    │         ├─ CIC (RTI appeals, decisions)
    │         ├─ IndiaCode (RTI Act full text)
    │         ├─ NALSA (legal aid)
    │         ├─ WCD Ministry (domestic violence)
    │         └─ Nyaaya (plain-language law summaries)
    │
    │   If web fetch returns ≥ 300 chars → use as primary context
    │   If web fetch returns < 300 chars (blocked/timeout) → RAG fallback
    │
    └─► [2] ChromaDB semantic search
              → top-5 chunks from legal knowledge base
              → fused with web context when both available
```

---

## 3. Tech Stack

### Backend

| Library | Purpose |
|---|---|
| `fastapi` | API framework |
| `uvicorn` | ASGI server |
| `groq` | Llama 3.3 70B LLM inference |
| `chromadb` | Vector store for RAG |
| `sentence-transformers` / `ONNXMiniLM-L6-v2` | Embedding model |
| `httpx` | Async HTTP for gov portal fetching |
| `beautifulsoup4` | HTML text extraction from web pages |
| `fpdf2` | PDF generation |
| `python-dotenv` | Environment variable loading |
| `pydantic` | Request/response schema validation |

### Frontend

| Library | Purpose |
|---|---|
| `Next.js 14` | React framework, App Router |
| `TypeScript` | Type safety |
| `Tailwind CSS` | Styling |
| `Web Speech API` | Browser-native speech recognition |
| `lucide-react` | Icons |

---

## 4. Project Structure

```
project-nyaya/
│
├── backend/
│   ├── main.py                  # FastAPI app — all routes, models, LLM logic
│   ├── form_pdf_builder.py      # PDF generation (RTI / DV / Divorce)
│   ├── web_fetcher.py           # Async gov portal scraper
│   ├── test_web_fetch.py        # Manual test script for web fetcher
│   ├── requirements.txt         # Python dependencies
│   ├── .env                     # Secrets (gitignored)
│   ├── .env.example             # Template for .env
│   └── static/                  # Generated PDFs served here (gitignored)
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx         # Main page — text/mic toggle, result display
│   │   │   ├── layout.tsx       # Root layout, metadata
│   │   │   └── globals.css      # Global styles
│   │   ├── components/
│   │   │   ├── MicButton.tsx    # Web Speech API recorder + language selector
│   │   │   ├── FormCollector.tsx# Agentic form UI (pre-fill + missing fields)
│   │   │   ├── ResultCard.tsx   # AI analysis display card
│   │   │   ├── Timeline.tsx     # Step-by-step legal process timeline
│   │   │   └── DownloadButton.tsx # PDF download button
│   │   └── data/
│   │       └── timelines.js     # RTI / DV / Divorce step data
│   ├── .env.local               # Frontend env vars (gitignored)
│   └── package.json
│
├── .gitignore
├── README.md
└── DOCUMENTATION.md             # This file
```

---

## 5. Setup & Installation

### Prerequisites

- Python 3.10+
- Node.js 18+
- A [Groq API key](https://console.groq.com) (free tier available)

### Backend

```bash
cd backend

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate      # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure secrets
copy .env.example .env
# Edit .env and add your GROQ_API_KEY

# Start server
uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.  
Interactive docs: `http://localhost:8000/docs`

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Configure
# Create frontend/.env.local with:
# NEXT_PUBLIC_BACKEND_URL=http://localhost:8000

# Start dev server
npm run dev
```

App available at `http://localhost:3000`.

---

## 6. Environment Variables

### Backend (`backend/.env`)

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | Yes | Groq API key for Llama 3.3 70B |
| `DEMO_MODE` | No | Set `true` to run without API key (returns mock data) |

### Frontend (`frontend/.env.local`)

| Variable | Required | Description |
|---|---|---|
| `NEXT_PUBLIC_BACKEND_URL` | Yes | Backend API base URL (default: `http://localhost:8000`) |

---

## 7. Backend API Reference

Base URL: `http://localhost:8000`

---

### `POST /api/analyze`

Analyses user text and returns structured legal guidance.

**Request body:**
```json
{
  "text": "I want to file an RTI about my pension. My name is Ravi Kumar."
}
```

**Response:**
```json
{
  "intent_detected": "RTI | Domestic Violence | Divorce | Unknown",
  "kill_switch_triggered": false,
  "simplified_explanation": "Under Section 6(1) RTI Act 2005...",
  "relevant_acts": ["Section 6(1), RTI Act 2005 — Filing procedure"],
  "immediate_action_steps": ["Step 1...", "Step 2..."],
  "extracted_user_issue": "User wants RTI about pension delay",
  "follow_up_question": "Which government department handles your pension?",
  "context_source": "WEB+RAG | RAG",
  "sources_used": ["https://cic.gov.in/..."]
}
```

**Kill switch:** Set to `true` when query is outside scope (income tax, property disputes, subjective opinions). No legal guidance is returned.

---

### `POST /api/extract_form`

Extracts structured form fields from the user's voice/text using LLM.

**Request body:**
```json
{
  "text": "My name is Priya Sharma, I live at 45 MG Road Chennai. My husband Ramesh is beating me.",
  "intent": "Domestic Violence"
}
```

**Response:**
```json
{
  "intent": "Domestic Violence",
  "form_data": {
    "complainant_name": "Priya Sharma",
    "complainant_address": "45 MG Road Chennai",
    "respondent_name": "Ramesh",
    "respondent_relation": "husband",
    "nature_of_violence": ["Physical"],
    "complainant_age": null,
    "incident_date": null
  },
  "missing_fields": ["complainant_age", "incident_date", "witnesses"],
  "missing_questions": [
    "What is your age?",
    "When did the most recent incident occur?"
  ]
}
```

**Extraction rules:** Only extracts what the user explicitly stated. Fields not mentioned are returned as `null`.

---

### `POST /api/generate_form_pdf`

Generates a formatted legal document PDF from completed form data.

**Request body:**
```json
{
  "intent": "RTI | Domestic Violence | Divorce",
  "form_data": { ... }
}
```

**Response:**
```json
{
  "pdf_url": "/static/nyaya_form_<uuid>.pdf",
  "pdf_filename": "nyaya_form_<uuid>.pdf",
  "intent": "Domestic Violence"
}
```

The PDF is served as a static file at `http://localhost:8000/static/<filename>`.

---

### `POST /api/generate_pdf`

Generates a summary PDF of the AI legal analysis result (not a form — a guidance document).

**Request body:** Full `IntentResult` object from `/api/analyze`.

**Response:**
```json
{ "pdf_url": "/static/<uuid>.pdf" }
```

---

### `POST /api/transcribe`

Transcribes uploaded audio using OpenAI Whisper.

> **Note:** This endpoint requires an `OPENAI_API_KEY`. Currently, the frontend uses the **browser-native Web Speech API** (`webkitSpeechRecognition`) instead, so this endpoint is not used in the default flow. It is available for future use.

**Request:** `multipart/form-data` with field `audio` (WebM/Opus file).

**Response:**
```json
{ "text": "Transcribed text here" }
```

---

### `POST /api/process`

Combined endpoint: transcribes audio → analyses → returns result in one call.

**Request:** `multipart/form-data` with field `audio`.

**Response:** Same as `/api/analyze`.

---

### `GET /api/debug/retrieve?query=<text>&intent=<intent>`

Debug endpoint: returns the top RAG chunks retrieved for a query.

**Response:**
```json
{
  "query": "how to file RTI",
  "intent": "RTI",
  "chunks_retrieved": 5,
  "results": [{ "id": "...", "text": "...", "distance": 0.12 }]
}
```

---

### `GET /api/debug/sources`

Returns the list of configured government portal sources.

**Response:**
```json
{
  "total_sources": 6,
  "sources": [{ "name": "CIC Portal", "url": "...", "topics": ["RTI"] }]
}
```

---

## 8. Frontend Components

### `page.tsx` — Main Page

Orchestrates the full user flow:
- **Text/Mic toggle** — switches between typed input and Web Speech API
- **Text mode** — textarea → `POST /api/analyze` → results
- **Mic mode** — `webkitSpeechRecognition` → transcript → `POST /api/analyze` → results
- Renders `ResultCard`, `Timeline`, agentic form CTA, `FormCollector` modal

---

### `MicButton.tsx` — Voice Input

Uses the browser-native **Web Speech API** (`webkitSpeechRecognition`).

| Feature | Detail |
|---|---|
| Languages | 11 Indian languages + English (dropdown selector) |
| Continuous mode | Stays recording; auto-restarts after Chrome's 5s silence timeout |
| Live preview | Shows final text (dark) + interim in-progress words (grey italic) |
| Stop behaviour | User taps stop → transcript submitted to `/api/analyze` |
| Fallback | Shows warning on Firefox/Safari (not supported) |

---

### `FormCollector.tsx` — Agentic Form UI

Shown after user clicks "Generate My Filled Document".

**On mount:**
1. Calls `POST /api/extract_form` with intent + transcribed text
2. Shows loading state while AI extracts fields

**Field display:**
- ✅ **Pre-filled (green)** — AI extracted from voice
- ⚠ **Missing (amber)** — user must fill manually; includes the specific question to answer

**On submit:**
- Calls `POST /api/generate_form_pdf` with all form data
- Shows a download link to the generated PDF

---

### `ResultCard.tsx` — Analysis Display

Displays the LLM response with:
- Intent badge (RTI / Domestic Violence / Divorce)
- Simplified explanation (with act citations)
- Relevant acts list
- Immediate action steps
- Your issue (as understood by AI)
- Follow-up question

---

### `Timeline.tsx` — Legal Process Steps

Shows a step-by-step graphical timeline for the detected legal category:
- **RTI:** Draft → File → Wait 30 days → First Appeal → Second Appeal (CIC)
- **DV:** Safety → Approach Protection Officer → File complaint → Court order
- **Divorce:** Both parties agree → File in Family Court → First Motion → Cooling off → Second Motion → Decree

---

### `DownloadButton.tsx` — PDF Download

Renders a prominent download button linking to the generated PDF URL.

---

## 9. Context Retrieval Pipeline

### Web Fetcher (`web_fetcher.py`)

Fetches live content from official Indian government portals before falling back to static RAG.

**Configured sources:**

| Source | URL | Topics |
|---|---|---|
| CIC Portal | cic.gov.in | RTI appeals, decisions |
| IndiaCode | indiacode.nic.in | RTI Act full text |
| NALSA | nalsa.gov.in | Legal aid entitlements |
| Ministry WCD | wcd.nic.in | Domestic violence, PWDVA |
| Nyaaya | nyaaya.org | Plain-language law summaries |

**Timeout:** 6 seconds per request

**Fallback trigger:** If combined web content is < 300 characters, ChromaDB RAG is used instead.

### ChromaDB RAG

- **Embedding model:** `ONNXMiniLM-L6-v2` (runs locally, no API key needed)
- **Storage:** In-memory ChromaDB client (populated at startup from `LEGAL_CHUNKS`)
- **Retrieval:** Top-5 semantically similar chunks for the user query
- **Chunk categories:** RTI Act 2005, PWDVA 2005, HMA 1955

---

## 10. Agentic Form Filling

### Flow

```
1. User speaks/types their situation
      │
2. /api/analyze → intent detected (RTI / DV / Divorce)
      │
3. User clicks "Generate My Filled Document"
      │
4. FormCollector mounts → calls /api/extract_form
      │  LLM reads the voice text and extracts:
      │  - Fields the user mentioned → pre-filled (green)
      │  - Fields not mentioned → null + question (amber)
      │
5. User fills in missing fields
      │
6. "Generate My Legal Document" → /api/generate_form_pdf
      │
7. Download ready-to-submit PDF draft
```

### Field Schemas

**RTI Application:**
- `name`, `address`, `phone`, `email`, `bpl_status`
- `department_name`, `department_address`, `pio_name`
- `information_requested`, `time_period`, `format_required`, `fee_payment_mode`

**DV Complaint:**
- `complainant_name`, `complainant_age`, `complainant_address`, `complainant_phone`
- `respondent_name`, `respondent_relation`, `respondent_address`
- `nature_of_violence` (array: Physical/Sexual/Verbal/Emotional/Economic/Dowry)
- `incident_date`, `incident_description`, `witnesses`
- `children` (array of `{name, age}`)
- `relief_protection`, `relief_residence`, `relief_monetary_amount`, `relief_custody`

**Divorce Petition:**
- `petitioner1_name/age/occupation/address`, `petitioner2_name/age/occupation/address`
- `marriage_date`, `marriage_place`, `marriage_registration_number`
- `separation_date`, `separation_address`
- `children` (array)
- `alimony_amount`, `alimony_terms`, `custody_arrangement`
- `stridhan_settled`, `property_settled`

---

## 11. PDF Generation

Module: `form_pdf_builder.py`

Three document builders — all use `fpdf2` with Helvetica (Latin-1 safe, no Unicode fonts required):

| Function | Document | Legal Basis |
|---|---|---|
| `build_rti_pdf(data, path)` | RTI Application | Section 6, RTI Act 2005 |
| `build_dv_pdf(data, path)` | DV Complaint to Protection Officer | Section 12, PWDVA 2005 |
| `build_divorce_pdf(data, path)` | Mutual Consent Divorce Petition | Section 13B, HMA 1955 |

### PDF Structure (each document)

1. **Nyaya header bar** (dark navy) with branding
2. **Document title block** (blue) with legal citation
3. **Numbered sections** with labelled fields:
   - Green filled text = extracted from voice
   - Blank underline = missing (must be filled before submission)
4. **Procedure box** ("How to File This Document")
5. **Legal disclaimer** (amber box — draft only, not legal advice)

---

## 12. Legal Knowledge Base

Built-in RAG chunks cover (defined in `main.py → LEGAL_CHUNKS`):

### RTI Act 2005
- Scope and definitions (Section 2(f))
- Right to information and obligations of public authorities
- Filing procedure — Section 6 application to PIO
- Time limits — 30 days standard, 48 hours (life/liberty)
- Fee structure — Rs. 10 general, BPL exempt
- Exemptions — Section 8 (national security, Cabinet papers etc.)
- Appeals — First appeal to FAA, Second appeal to CIC
- Penalties — Section 20 Rs. 250/day up to Rs. 25,000
- Online RTI — rtionline.gov.in

### PWDVA 2005 (Domestic Violence Act)
- Definition — Section 3 (physical, sexual, verbal, emotional, economic)
- Aggrieved person definition — any woman in a domestic relationship
- Reliefs — Section 18 (protection order), 19 (residence), 20 (monetary), 21 (custody)
- Protection Officer role — free assistance, file complaint
- Emergency order — within 3 days
- Section 498A IPC — dowry harassment (criminal parallel)
- Helpline: 181 (Women Helpline), 100 (Police)

### HMA 1955 (Hindu Marriage Act)
- Section 13 — Divorce grounds (cruelty, desertion, adultery etc.)
- Section 13B — Mutual Consent Divorce
- Procedure — First Motion, 6-month cooling off, Second Motion
- Cooling-off waiver — Amardeep Singh v. Harveen Kaur, SC 2017
- Alimony — Section 25 permanent alimony
- Child custody — Section 26
- Minimum separation — 1 year required for Section 13B

---

## 13. Deployment

### Backend (Render / Railway / Fly.io)

1. Set environment variable `GROQ_API_KEY`
2. Set start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
3. Set `DEMO_MODE=false`
4. Note: ChromaDB runs in-memory — no persistent storage needed; knowledge base is re-seeded on every startup

### Frontend (Vercel)

1. Set environment variable `NEXT_PUBLIC_BACKEND_URL` = your backend URL
2. Deploy from `/frontend` directory
3. Build command: `npm run build`
4. Output: `.next`

> **CORS note:** Backend is configured with `allow_origins=["*"]` for development. Restrict this in production to your frontend domain.

---

## 14. Disclaimer

> Project Nyaya is **not a law firm** and does **not provide legal advice**. All documents generated are **AI-assisted drafts for informational purposes only**.
>
> Before filing any document, users should:
> - Review the document with a qualified legal aid advocate or lawyer
> - Fill in all fields marked as blank/missing
> - Verify accuracy of act citations for their specific state/jurisdiction
>
> **Emergency contacts:**
> - Police: **100**
> - Women Helpline: **181** (24x7, Free)
> - NALSA Legal Aid: **15100**
> - One Stop Centre: **181**
