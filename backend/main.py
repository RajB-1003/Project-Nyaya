"""
Project Nyaya — FastAPI Backend v5.0
Voice-first legal triage for marginalized communities.

Context retrieval pipeline (priority order):
  1. Live web fetch from official Indian government portals (httpx, async, 6s timeout)
  2. ChromaDB semantic search (ONNXMiniLM-L6-v2) — fallback if web fetch returns < 300 chars
  3. Both sources are fused when web fetch succeeds, so the LLM gets the richest possible context
"""

import asyncio
import os
import uuid
import json
import tempfile
from pathlib import Path
from typing import List

import chromadb
from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2
from groq import Groq
from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from fpdf import FPDF

from web_fetcher import fetch_government_context, get_available_sources, GOVERNMENT_SOURCES

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

load_dotenv()
DEMO_MODE: bool = os.getenv("DEMO_MODE", "false").lower() == "true"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not DEMO_MODE and not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY is not set. Add it to .env or set DEMO_MODE=true.")

groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Project Nyaya API", version="4.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ---------------------------------------------------------------------------
# ChromaDB — Semantic Retrieval Engine
# ---------------------------------------------------------------------------
# Uses ONNXMiniLM-L6-v2 (built into chromadb, no torch required, ~23MB)
# In-memory store: repopulated on every server start from LEGAL_CHUNKS below.
# ---------------------------------------------------------------------------

_chroma_client = chromadb.Client()
_embed_fn = ONNXMiniLM_L6_V2()

LEGAL_CHUNKS = [
    # ── RTI Act, 2005 ──────────────────────────────────────────────────────
    {
        "id": "rti_scope_definition",
        "topic": "RTI",
        "section": "Scope and Definitions",
        "text": (
            "RTI Act 2005 — Scope and Who Can File: "
            "Section 2(f) defines 'Information' as any material in any form — records, documents, memos, "
            "emails, opinions, advices, press releases, circulars, orders, logbooks, contracts, reports, "
            "samples, models, and electronic data. "
            "Section 2(h) defines 'Public Authority' as any body established by the Constitution, Parliament, "
            "State Legislature, or Government notification — includes all central/state departments, PSUs, "
            "government-aided institutions, banks, courts (except Supreme Court registry). "
            "Section 2(j): Every citizen of India has the right to inspect records, obtain certified copies, "
            "and take certified samples of material held by public authorities. "
            "RTI does NOT apply to intelligence agencies listed in Second Schedule (e.g., RAW, IB) "
            "except on matters of corruption or human rights violations (Section 24)."
        ),
    },
    {
        "id": "rti_filing_procedure",
        "topic": "RTI",
        "section": "Filing Procedure",
        "text": (
            "RTI Act 2005 — How to File an RTI Application (Section 6): "
            "Write a plain application in English, Hindi, or any official language of the area. "
            "Address it to the Public Information Officer (PIO) of the relevant department. "
            "NO reasons or justification required — Section 6(1) explicitly states this. "
            "Pay fee of Rs. 10 by Indian Postal Order (IPO), Demand Draft, court fee stamp, or cash. "
            "BPL (Below Poverty Line) card holders are FULLY EXEMPT from all fees — attach BPL card copy. "
            "File ONLINE at rtionline.gov.in for all central government departments. "
            "File by speed post / registered post or in person at the department office. "
            "Section 6(3): If the PIO of the wrong department receives your application, they MUST transfer "
            "it to the correct public authority within 5 days and inform you."
        ),
    },
    {
        "id": "rti_timelines_deadlines",
        "topic": "RTI",
        "section": "Timelines and Deadlines",
        "text": (
            "RTI Act 2005 — Timelines and Deadlines: "
            "Section 7(1): The PIO must provide information within 30 days of receiving the application. "
            "Section 7(1) Proviso: If information concerns the life or liberty of a person, the PIO must respond "
            "within 48 HOURS. Courts have interpreted 'life and liberty' broadly to include ration cards, MGNREGA wages, "
            "pension disbursement, and police safety. "
            "Section 7(2): If information pertains to a third party, the PIO gets 40 days to respond. "
            "Section 7(5): If the PIO misses the 30-day deadline, information must be provided FREE OF COST. "
            "Section 7(6): Partial disclosure — PIO can supply part of the information and deny the rest with reasons. "
            "Deemed Refusal: If PIO does not respond within 30 days, it is treated as a refusal and the applicant "
            "can immediately file a First Appeal."
        ),
    },
    {
        "id": "rti_fees_charges",
        "topic": "RTI",
        "section": "Fees and Charges",
        "text": (
            "RTI Act 2005 — Detailed Fee Structure: "
            "Application fee: Rs. 10 (IPO, DD, court fee stamp, or cash). "
            "BPL applicants: ZERO fee for application AND information — attach BPL card copy. "
            "Information fee: Rs. 2 per page (A4 or A3 size), Rs. 5 per page (larger), "
            "Rs. 50 per diskette or floppy, actual cost for samples/models. "
            "Inspection of records: Rs. 5 per hour (first hour free). "
            "First Appeal: FREE — no fee. "
            "Second Appeal to CIC/SIC: FREE — no fee. "
            "If PIO misses 30-day deadline under Section 7(5): ALL information provided free of cost. "
            "State governments set their own fee schedules — some states charge Rs. 10, others charge differently."
        ),
    },
    {
        "id": "rti_appeals_process",
        "topic": "RTI",
        "section": "Appeals — First and Second",
        "text": (
            "RTI Act 2005 — Appeals Process: "
            "Section 19(1) — First Appeal: File with the First Appellate Authority (an officer senior to the PIO "
            "in the same department) within 30 days of receiving an unsatisfactory reply or 30+30=60 days from filing "
            "if no reply. First Appeal is FREE. The First Appellate Authority must decide within 30 days (extendable to 45). "
            "Section 19(3) — Second Appeal: If First Appeal fails or no response, file with the Central Information Commission (CIC) "
            "for central government, or State Information Commission (SIC) for state government. "
            "File within 90 days of the First Appellate Authority's order. FREE. "
            "Section 19(8): CIC/SIC can require the public authority to disclose information, appoint a new PIO, "
            "publish certain information, or compensate the complainant. "
            "Section 20 — Penalty: CIC/SIC can impose a penalty of Rs. 250 per day of delay on the PIO, "
            "up to a maximum of Rs. 25,000. Disciplinary action can also be recommended."
        ),
    },
    {
        "id": "rti_exemptions",
        "topic": "RTI",
        "section": "Exemptions from Disclosure",
        "text": (
            "RTI Act 2005 — What Information Can Be Withheld (Section 8): "
            "Section 8(1)(a): National security, sovereignty, strategic/scientific interest. "
            "Section 8(1)(b): Information that courts have forbidden from publication. "
            "Section 8(1)(c): Parliamentary privilege. "
            "Section 8(1)(d): Commercial confidence, trade secrets, intellectual property. "
            "Section 8(1)(e): Information held in fiduciary relationship (e.g., advice given to ministers). "
            "Section 8(1)(g): Information that would endanger the life of a person. "
            "Section 8(1)(h): Information that would impede ongoing investigation or prosecution. "
            "Section 8(1)(j): Personal information with no public interest — frequently misused by public authorities; "
            "CIC has held that salary, assets, and conduct of public servants IS disclosable. "
            "Section 8(2): Even exempt information must be disclosed if there is overriding public interest. "
            "Third-Party Information (Section 11): PIO must give 5 days notice to the third party before disclosing."
        ),
    },

    # ── Protection of Women from Domestic Violence Act, 2005 ───────────────
    {
        "id": "dv_definition_types",
        "topic": "Domestic Violence",
        "section": "Definition and Types of Abuse",
        "text": (
            "Protection of Women from Domestic Violence Act 2005 (PWDVA) — What Counts as Domestic Violence: "
            "Section 3 defines domestic violence to include: "
            "Physical Abuse: Any act causing bodily pain, harm, or danger to life — hitting, slapping, kicking, "
            "punching, pushing, burning, biting, hair-pulling, use of weapons. "
            "Sexual Abuse: Any conduct of a sexual nature that humiliates, degrades, or violates dignity. "
            "Verbal and Emotional Abuse: Insults, ridicule, humiliation, name-calling, threats of physical harm, "
            "threats to take away children, threats of divorce, controlling behaviour, isolating from family. "
            "Economic Abuse (Section 3(iv)): Depriving the woman of financial resources she is entitled to, "
            "refusing to pay rent, forcing her to leave the shared household, disposing of stridhan/property. "
            "Dowry Demands (Section 3(iv)(c)): Repeated demands for dowry or valuable property constitute "
            "domestic violence. This is SEPARATE from the Dowry Prohibition Act 1961."
        ),
    },
    {
        "id": "dv_who_can_file_officials",
        "topic": "Domestic Violence",
        "section": "Who Can File and Key Officials",
        "text": (
            "PWDVA 2005 — Who Can File and Key Officials: "
            "Section 2(a) — Aggrieved Person: Any woman who is or has been in a domestic relationship "
            "and alleges domestic violence. Includes wife, live-in partner, sister, mother, daughter. "
            "Section 2(q) — Respondent: Male adult member of the household or relatives of the husband/partner. "
            "Who can approach: The woman herself, any person on her behalf, a child of the aggrieved woman, "
            "a Protection Officer, or a police officer. "
            "Protection Officer (Section 9): Appointed by State Government. Service is FREE. "
            "Duties: Prepare DIR, assist in court, arrange shelter/medical aid, ensure safety plan. "
            "Service Provider (Section 10): Registered NGOs can receive complaints, provide shelter, legal aid. "
            "Magistrate (Section 12): Any Judicial/Metropolitan Magistrate has jurisdiction. "
            "The aggrieved woman can file directly with the Magistrate, bypassing the Protection Officer."
        ),
    },
    {
        "id": "dv_dir_filing",
        "topic": "Domestic Violence",
        "section": "Domestic Incident Report Filing",
        "text": (
            "PWDVA 2005 — Filing the Domestic Incident Report (DIR) and Approaching the Magistrate: "
            "Step 1: Contact Protection Officer at the district court or Police Station or DLSA (District Legal Services Authority) — FREE. "
            "Step 2: Protection Officer is LEGALLY OBLIGATED under Section 9(b) to prepare the DIR in Form I. "
            "DIR can also be prepared by a Service Provider under Section 10(2)(c). "
            "Step 3: Protection Officer files the DIR with the Magistrate under Section 12. "
            "You can also directly file a petition/application under Section 12(1) to the Magistrate yourself. "
            "Section 12(4): Magistrate MUST fix the first hearing date within 3 DAYS of receiving application. "
            "Section 12(5): All proceedings must be disposed of within 60 DAYS. "
            "All proceedings are held in camera (private) to protect dignity — Section 16. "
            "EMERGENCY: Call Women Helpline 181 (24x7) or Police 100. Police MUST assist under Section 5."
        ),
    },
    {
        "id": "dv_court_orders",
        "topic": "Domestic Violence",
        "section": "Court Orders Available",
        "text": (
            "PWDVA 2005 — Orders the Magistrate Can Pass: "
            "Protection Order (Section 18): Prohibits respondent from committing DV, entering victim's workplace "
            "or school, contacting or communicating with the victim, alienating her assets or stridhan. "
            "Violation of a Protection Order is a CRIMINAL OFFENCE — Section 31 — imprisonment up to 1 year "
            "or fine up to Rs. 20,000 or both. "
            "Residence Order (Section 19): Respondent must vacate the shared household. The victim CANNOT be "
            "dispossessed from the shared household even if she has no ownership. The respondent must provide "
            "alternative accommodation of same standard. "
            "Monetary Relief (Section 20): Covers loss of earnings, medical expenses, maintenance for herself "
            "and children, and cost of rented accommodation. Paid by the respondent. "
            "Custody Order (Section 21): Interim custody of children to the aggrieved person. "
            "Compensation and Damages (Section 22): Lump-sum compensation for physical/mental injuries, "
            "emotional distress, and mental torture caused by domestic violence."
        ),
    },
    {
        "id": "dv_criminal_remedies",
        "topic": "Domestic Violence",
        "section": "Criminal Law Remedies",
        "text": (
            "Parallel Criminal Remedies for Domestic Violence Victims: "
            "Section 498A IPC (now Section 85 BNS 2023): Cruelty by husband or relatives. "
            "Cognizable (police can arrest without warrant), non-bailable. Imprisonment up to 3 years + fine. "
            "Section 304B IPC (now Section 80 BNS 2023): Dowry death — woman dies within 7 years of marriage "
            "in suspicious circumstances. Minimum 7 years imprisonment, maximum life. Presumption against husband. "
            "Section 323/325 IPC (now Sections 115/117 BNS): Simple/grievous hurt — up to 1 to 7 years. "
            "Section 354 IPC (now Section 74 BNS): Assault or criminal force to outrage modesty. "
            "Section 506 IPC (now Section 351 BNS): Criminal intimidation — threats. "
            "Dowry Prohibition Act 1961: Section 4 — demanding dowry punishable by minimum 6 months imprisonment "
            "and fine of Rs. 5,000 minimum. "
            "HELPLINES: National Women Helpline: 181 (free, 24x7) | Police: 100 | "
            "National Commission for Women: 011-26942369 | District Legal Services Authority (DLSA): Free legal aid."
        ),
    },

    # ── Hindu Marriage Act, 1955 — Divorce ────────────────────────────────
    {
        "id": "divorce_eligibility_types",
        "topic": "Divorce",
        "section": "Eligibility and Types of Divorce",
        "text": (
            "Hindu Marriage Act 1955 — Divorce: Types and Eligibility: "
            "Mutual Consent Divorce — Section 13B: Both spouses agree. Must have lived separately for AT LEAST 1 YEAR. "
            "Both must appear before the Family Court. Faster, less adversarial. "
            "Contested Divorce — Section 13: Grounds include cruelty (Section 13(1)(ia)), adultery (Section 13(1)(i)), "
            "desertion for 2+ years (Section 13(1)(ib)), conversion to another religion, mental disorder, "
            "venereal disease, renunciation of the world, presumption of death. "
            "Special Marriage Act 1954 — Section 28: Mutual consent divorce for inter-religious marriages. "
            "Similar to 13B but requires 1-year separation. "
            "Muslim Personal Law: Talaq-e-Ahsan (most approved form — 3 monthly periods), Khula (wife-initiated). "
            "Triple Talaq is ABOLISHED — Muslim Women (Protection of Rights on Marriage) Act 2019. "
            "Christian Divorce: Indian Divorce Act 1869 — Section 10A: Mutual consent, 2-year separation required."
        ),
    },
    {
        "id": "divorce_procedure_steps",
        "topic": "Divorce",
        "section": "Step-by-Step Mutual Consent Procedure",
        "text": (
            "Section 13B, Hindu Marriage Act 1955 — Mutual Consent Divorce Procedure: "
            "Pre-Requisites: Both must agree. Must have lived separately for 1 year or more IMMEDIATELY before filing. "
            "Step 1 — Settlement: Before filing, BOTH parties must settle in a Memorandum of Understanding (MOU): "
            "alimony amount and payment schedule, child custody and visitation rights, return of stridhan, "
            "division of property. Courts insist on complete settlement to avoid future disputes. "
            "Step 2 — Engage Advocate: Draft joint petition signed by BOTH spouses. "
            "Step 3 — File in Family Court: Jurisdiction = where marriage was solemnized OR where the respondent "
            "resides OR where parties last lived together. Court fee: approximately Rs. 200-500. "
            "Step 4 — First Motion (Section 13B(1)): Both appear before judge on same day. Statements recorded on oath. "
            "First Motion granted. A 6-month cooling-off period begins. "
            "Step 5 — Second Motion (Section 13B(2)): Must be filed within 18 months of First Motion. "
            "Both appear again to confirm consent. Decree of Divorce passed immediately. "
            "Cooling-Off Waiver: Supreme Court in Amardeep Singh v. Harveen Kaur (2017) — courts CAN waive "
            "the 6-month period if: marriage is irretrievably broken, all issues settled, waiting would prolong suffering."
        ),
    },
    {
        "id": "divorce_alimony_maintenance",
        "topic": "Divorce",
        "section": "Alimony and Maintenance",
        "text": (
            "Alimony and Maintenance Laws in India — Divorce Context: "
            "Section 24, Hindu Marriage Act 1955: Maintenance pendente lite — maintenance DURING the divorce proceedings "
            "for whichever spouse earns less. Either husband or wife can claim. Court passes order within 60 days. "
            "Section 25, HMA 1955: Permanent alimony — lump sum or monthly amount awarded AFTER divorce decree. "
            "Court considers: income and property of both parties, conduct of the parties, other circumstances. "
            "Either spouse can claim. Can be revisited if circumstances change. "
            "Section 125, CrPC (now Section 144 BNSS 2023): Magistrate can order monthly maintenance for wife, "
            "children, and parents — Rs. amount determined by court. Can be obtained quickly even before Family Court divorce. "
            "Women can file under BOTH Section 125 CrPC AND Hindu Marriage Act simultaneously. "
            "Stridhan: All jewellery, gifts, and property given to the wife at or before/ after marriage from any source "
            "is her absolute property — Supreme Court in Pratibha Rani v. Suraj Kumar (1985). "
            "Husband has NO right to stridhan even during marriage."
        ),
    },
    {
        "id": "divorce_child_custody",
        "topic": "Divorce",
        "section": "Child Custody",
        "text": (
            "Child Custody Laws in India — Divorce Context: "
            "Section 26, Hindu Marriage Act 1955: Court can pass interim or permanent custody orders at any stage, "
            "even before the divorce decree. Best interest of the child is the paramount consideration. "
            "Guardians and Wards Act 1890: The applicable law for custody disputes. Section 13 — welfare of the minor is first. "
            "General Practice: Mother usually gets custody of children below 5 years (tender years doctrine). "
            "For children above 5, the court considers: the child's own preference (if old enough), "
            "stability of home, financial capacity of each parent, relationship with siblings. "
            "Father has the right to visitation even when mother has custody. "
            "NRI Custody: If one parent takes child abroad without consent, the other parent can file a Habeas Corpus petition "
            "in the High Court. India is not a signatory to the Hague Convention. "
            "Interim Custody: Can be obtained urgently from the Family Court within days of filing. "
            "Section 21, PWDVA 2005: Even in domestic violence cases, the Magistrate can grant temporary custody."
        ),
    },
    {
        "id": "divorce_nri_special",
        "topic": "Divorce",
        "section": "NRI Divorce and Other Special Situations",
        "text": (
            "Special Divorce Situations — NRI, Muslim, Christian: "
            "NRI Divorce (Hindu Marriage Act): Section 19 — petition can be filed in India even if one party is abroad. "
            "The spouse abroad can appoint a Power of Attorney holder to appear in court during proceedings, "
            "but MUST appear in person for the Final Hearing. "
            "Foreign Divorce Decrees: Not automatically valid in India. Must be enforced through Indian courts. "
            "Muslim Divorce: Triple talaq ABOLISHED under Muslim Women (Protection of Rights on Marriage) Act 2019 — "
            "instant triple talaq is a CRIMINAL OFFENCE with up to 3 years imprisonment. "
            "Dissolution of Muslim Marriages Act 1939: Wife can seek divorce on grounds of husband's whereabouts unknown, "
            "failure to maintain, imprisonment, cruelty, impotency, mental disorder, leprosy. "
            "Khula: Wife-initiated divorce — she typically returns mehr (dower) received at nikah. "
            "Christian Divorce: Indian Divorce Act 1869 as amended — Section 10A mutual consent requires 2-year separation."
        ),
    },
]

# ---------------------------------------------------------------------------
# Build / rebuild the ChromaDB collection at module load
# ---------------------------------------------------------------------------


def _build_vector_store() -> chromadb.Collection:
    """Embed all legal chunks and store in an in-memory ChromaDB collection."""
    try:
        _chroma_client.delete_collection("nyaya_legal")
    except Exception:
        pass

    collection = _chroma_client.create_collection(
        name="nyaya_legal",
        embedding_function=_embed_fn,
        metadata={"hnsw:space": "cosine"},
    )
    collection.add(
        ids=[c["id"] for c in LEGAL_CHUNKS],
        documents=[c["text"] for c in LEGAL_CHUNKS],
        metadatas=[{"topic": c["topic"], "section": c["section"]} for c in LEGAL_CHUNKS],
    )
    return collection


# Build the store at import time (first request might be slightly slower)
_collection: chromadb.Collection = _build_vector_store()


def semantic_retrieve(query: str, n_results: int = 4) -> str:
    """
    Embed the user's query and return the top-n most semantically relevant
    legal chunk texts, joined together as a single context string.
    """
    results = _collection.query(
        query_texts=[query],
        n_results=n_results,
        include=["documents", "metadatas"],
    )
    docs = results["documents"][0]        # list of chunk texts
    metas = results["metadatas"][0]       # list of metadata dicts
    context_parts = []
    for doc, meta in zip(docs, metas):
        context_parts.append(f"[{meta['topic']} — {meta['section']}]\n{doc}")
    return "\n\n".join(context_parts)


# ---------------------------------------------------------------------------
# Audio MIME types
# ---------------------------------------------------------------------------

AUDIO_MIME_MAP = {
    ".webm": "audio/webm",
    ".mp3":  "audio/mpeg",
    ".mp4":  "audio/mp4",
    ".wav":  "audio/wav",
    ".ogg":  "audio/ogg",
    ".flac": "audio/flac",
    ".m4a":  "audio/mp4",
}


def get_mime_type(suffix: str) -> str:
    return AUDIO_MIME_MAP.get(suffix.lower(), "audio/webm")


# ---------------------------------------------------------------------------
# Demo-mode canned responses (no API calls)
# ---------------------------------------------------------------------------

DEMO_RESPONSES = {
    "RTI": {
        "intent_detected": "RTI",
        "kill_switch_triggered": False,
        "simplified_explanation": (
            "Under Section 6(1) of the Right to Information Act 2005, you have the right to request "
            "information from any public authority without giving reasons. The Public Information Officer (PIO) "
            "must respond within 30 days under Section 7(1), or within 48 hours if it concerns your life or livelihood."
        ),
        "relevant_acts": [
            "Section 6(1), RTI Act 2005 — Right to file application; no reasons required",
            "Section 7(1), RTI Act 2005 — PIO must respond within 30 days (48 hrs for life/liberty)",
            "Section 19(1), RTI Act 2005 — First appeal within 30 days of refusal or non-reply",
            "Section 20, RTI Act 2005 — Penalty of Rs. 250/day (max Rs. 25,000) on erring PIO",
        ],
        "immediate_action_steps": [
            "Identify the Public Information Officer (PIO) of the relevant government department.",
            "Write a clear application stating EXACTLY what information you want — no reasons needed.",
            "Pay Rs. 10 fee by IPO/DD/court fee stamp (BPL cardholders are fully exempt).",
            "Submit in person, by registered post, or online at rtionline.gov.in.",
            "If PIO does not reply within 30 days, file a FREE First Appeal immediately.",
        ],
        "extracted_user_issue": "The user wants to file an RTI application to obtain information from a government department.",
        "follow_up_question": "Which specific government department or service are you requesting information from?",
        "transcribed_text": "[DEMO] I want to file an RTI to get information about my ration card from the government.",
    },
    "Domestic Violence": {
        "intent_detected": "Domestic Violence",
        "kill_switch_triggered": False,
        "simplified_explanation": (
            "Under Section 3 of the Protection of Women from Domestic Violence Act 2005, what you are "
            "experiencing qualifies as domestic violence. You can obtain an emergency Protection Order from "
            "the Magistrate under Section 18 within 3 days of filing — this legally prevents the abuser "
            "from contacting or approaching you."
        ),
        "relevant_acts": [
            "Section 3, PWDVA 2005 — Definition of domestic violence (physical, emotional, economic, sexual)",
            "Section 18, PWDVA 2005 — Protection Order (emergency, legally binding)",
            "Section 19, PWDVA 2005 — Residence Order (abuser must vacate shared household)",
            "Section 498A IPC (Section 85 BNS) — Cruelty by husband, non-bailable offence",
            "Section 20, PWDVA 2005 — Monetary relief for medical expenses and loss of earnings",
        ],
        "immediate_action_steps": [
            "Call Women Helpline 181 (free, 24x7) or Police 100 if you are in immediate danger.",
            "Contact the Protection Officer at your district court or nearest police station — service is FREE.",
            "Ask the Protection Officer to prepare a Domestic Incident Report (DIR) under Section 9(b).",
            "The Magistrate will fix a hearing within 3 days and can issue a Protection Order immediately.",
            "Consider filing under Section 498A IPC simultaneously for criminal action against the abuser.",
        ],
        "extracted_user_issue": "The user is experiencing domestic violence and needs legal protection and remedies.",
        "follow_up_question": "Is the abuse physical, emotional, or economic — and are you currently living in the same household as the abuser?",
        "transcribed_text": "[DEMO] My husband is beating me and I want to file a domestic violence case.",
    },
    "Divorce": {
        "intent_detected": "Divorce",
        "kill_switch_triggered": False,
        "simplified_explanation": (
            "For mutual consent divorce under Section 13B(1) of the Hindu Marriage Act 1955, both spouses "
            "must agree and must have lived separately for at least 1 year. After the First Motion hearing, "
            "there is a 6-month cooling off period (which can be waived by the Supreme Court ruling in "
            "Amardeep Singh v. Harveen Kaur 2017 if the marriage is irretrievably broken)."
        ),
        "relevant_acts": [
            "Section 13B(1), Hindu Marriage Act 1955 — Mutual consent divorce with 1-year separation",
            "Section 13B(2), HMA 1955 — Second motion within 18 months; 6-month cooling off period",
            "Amardeep Singh v. Harveen Kaur (SC 2017) — Courts can waive the 6-month period",
            "Section 25, HMA 1955 — Permanent alimony and maintenance",
            "Section 26, HMA 1955 — Child custody arrangements",
        ],
        "immediate_action_steps": [
            "Settle alimony amount, child custody, and stridhan/property division before filing.",
            "Draft a joint petition signed by BOTH spouses with the help of a lawyer.",
            "File in the Family Court of the district where you last lived together (court fee ~Rs. 200-500).",
            "Attend First Motion hearing together — the judge records your statements on oath.",
            "Wait 6 months (or apply for waiver citing irretrievable breakdown) then attend Second Motion.",
        ],
        "extracted_user_issue": "Both spouses have mutually agreed to end the marriage and want to file for divorce.",
        "follow_up_question": "Have you and your spouse already completed 1 year of living separately, and have you settled alimony and custody?",
        "transcribed_text": "[DEMO] My spouse and I both want a mutual divorce. How do we proceed?",
    },
}


def _demo_process(intent_key: str = "RTI") -> dict:
    return DEMO_RESPONSES.get(intent_key, DEMO_RESPONSES["RTI"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class AnalyzeRequest(BaseModel):
    text: str


class IntentResult(BaseModel):
    intent_detected: str = Field(description="One of: RTI, Domestic Violence, Divorce, or Unknown")
    kill_switch_triggered: bool = Field(description="True if out of scope or asking for subjective legal advice")
    simplified_explanation: str = Field(description="Specific, tailored explanation citing relevant act sections (max 4 sentences)")
    relevant_acts: List[str] = Field(description="List of 3-5 specific sections that apply")
    immediate_action_steps: List[str] = Field(description="Specific, tailored action steps for THIS user's situation (4-6 items)")
    extracted_user_issue: str = Field(description="One-sentence summary of the user's specific problem")
    follow_up_question: str = Field(default="", description="One clarifying question. Empty string if not needed.")
    context_source: str = Field(
        default="RAG",
        description="'WEB' if context came from live government portal fetch, 'RAG' if from ChromaDB fallback, 'WEB+RAG' if both"
    )
    sources_used: List[str] = Field(
        default=[],
        description="List of government portal URLs/names that contributed to the answer"
    )


from form_pdf_builder import build_rti_pdf, build_dv_pdf, build_divorce_pdf


class GeneratePdfRequest(BaseModel):
    intent_detected: str
    kill_switch_triggered: bool
    simplified_explanation: str
    relevant_acts: List[str] = []
    immediate_action_steps: List[str]
    extracted_user_issue: str
    follow_up_question: str = ""
    context_source: str = "RAG"
    sources_used: List[str] = []


# ---------------------------------------------------------------------------
# Form extraction — Pydantic models & extraction prompt
# ---------------------------------------------------------------------------


class FormExtractRequest(BaseModel):
    text: str              # user's transcribed voice statement
    intent: str            # "RTI" | "Domestic Violence" | "Divorce"


class RTIFormData(BaseModel):
    name: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    bpl_status: str | None = None
    department_name: str | None = None
    department_address: str | None = None
    pio_name: str | None = None
    information_requested: str | None = None
    time_period: str | None = None
    format_required: str | None = None
    fee_payment_mode: str | None = None


class DVFormData(BaseModel):
    complainant_name: str | None = None
    complainant_age: str | None = None
    complainant_address: str | None = None
    complainant_phone: str | None = None
    respondent_name: str | None = None
    respondent_relation: str | None = None
    respondent_address: str | None = None
    nature_of_violence: List[str] = []
    incident_date: str | None = None
    incident_description: str | None = None
    witnesses: str | None = None
    children: list = []
    children_text: str | None = None
    relief_protection: bool = True
    relief_residence: bool = False
    relief_monetary_amount: str | None = None
    relief_custody: bool = False


class DivorceFormData(BaseModel):
    petitioner1_name: str | None = None
    petitioner1_age: str | None = None
    petitioner1_address: str | None = None
    petitioner1_occupation: str | None = None
    petitioner2_name: str | None = None
    petitioner2_age: str | None = None
    petitioner2_address: str | None = None
    petitioner2_occupation: str | None = None
    marriage_date: str | None = None
    marriage_place: str | None = None
    marriage_registration_number: str | None = None
    separation_date: str | None = None
    separation_address: str | None = None
    children: list = []
    children_text: str | None = None
    alimony_amount: str | None = None
    alimony_terms: str | None = None
    custody_arrangement: str | None = None
    stridhan_settled: str | None = None
    property_settled: str | None = None


# Unified response for the front-end form collector
class FormExtractResponse(BaseModel):
    intent: str
    form_data: dict                   # the extracted fields (may have nulls)
    missing_fields: List[str]         # list of field names that are still null
    missing_questions: List[str]      # human-readable questions to ask the user


# Prompt for field extraction
# Note: uses __SCHEMA__ and __TEXT__ as tokens (not {}) to avoid .format() conflicts with JSON braces
FORM_EXTRACT_PROMPT = """\
You are a form-filling assistant for an Indian legal app named Nyaya.

A user has described their legal situation in their own words. Your job is to extract specific form fields from what they said.

RULES:
- Only extract what the user ACTUALLY said. Do NOT invent or assume data.
- Set any field to null if the user did not mention it.
- For "nature_of_violence", return a JSON array of strings from: ["Physical", "Sexual", "Verbal", "Emotional", "Economic", "Dowry"].
- For "children", return a JSON array of objects: [{"name": "...", "age": "..."}]. If ages/names not given, return [].
- Return ONLY valid JSON matching the schema below. No markdown, no extra text.

__SCHEMA__

User statement: "__TEXT__"\
"""

_RTI_SCHEMA = """{
  "name": string|null,
  "address": string|null,
  "phone": string|null,
  "email": string|null,
  "bpl_status": string|null,
  "department_name": string|null,
  "department_address": string|null,
  "pio_name": string|null,
  "information_requested": string|null,
  "time_period": string|null,
  "format_required": string|null,
  "fee_payment_mode": string|null
}"""

_DV_SCHEMA = """{
  "complainant_name": string|null,
  "complainant_age": string|null,
  "complainant_address": string|null,
  "complainant_phone": string|null,
  "respondent_name": string|null,
  "respondent_relation": string|null,
  "respondent_address": string|null,
  "nature_of_violence": array of strings,
  "incident_date": string|null,
  "incident_description": string|null,
  "witnesses": string|null,
  "children": array of {name, age},
  "children_text": string|null,
  "relief_protection": boolean,
  "relief_residence": boolean,
  "relief_monetary_amount": string|null,
  "relief_custody": boolean
}"""

_DIVORCE_SCHEMA = """{
  "petitioner1_name": string|null,
  "petitioner1_age": string|null,
  "petitioner1_address": string|null,
  "petitioner1_occupation": string|null,
  "petitioner2_name": string|null,
  "petitioner2_age": string|null,
  "petitioner2_address": string|null,
  "petitioner2_occupation": string|null,
  "marriage_date": string|null,
  "marriage_place": string|null,
  "marriage_registration_number": string|null,
  "separation_date": string|null,
  "separation_address": string|null,
  "children": array of {name, age},
  "children_text": string|null,
  "alimony_amount": string|null,
  "alimony_terms": string|null,
  "custody_arrangement": string|null,
  "stridhan_settled": string|null,
  "property_settled": string|null
}"""

# Human-readable questions for each null field
_RTI_QUESTIONS = {
    "name": "What is your full name?",
    "address": "What is your complete postal address?",
    "phone": "What is your phone number?",
    "email": "What is your email address?",
    "bpl_status": "Do you hold a BPL (Below Poverty Line) card? (BPL cardholders are exempt from the Rs. 10 fee)",
    "department_name": "Which government department or office are you requesting information from?",
    "department_address": "What is the address of that department/office?",
    "pio_name": "Do you know the name of the Public Information Officer (PIO)? (Leave blank if unknown)",
    "information_requested": "What specific information do you want from the government?",
    "time_period": "For what time period do you want this information? (e.g., April 2023 to March 2024)",
    "format_required": "In what format do you want the information? (e.g., Certified true copies, Inspection of records)",
    "fee_payment_mode": "How will you pay the Rs. 10 fee? (Court fee stamp / Indian Postal Order / Demand Draft / Online at rtionline.gov.in)",
}

_DV_QUESTIONS = {
    "complainant_name": "What is your full name?",
    "complainant_age": "What is your age?",
    "complainant_address": "What is your current address (a safe address you can receive correspondence at)?",
    "complainant_phone": "What is your phone number?",
    "respondent_name": "What is the full name of the person committing the violence?",
    "respondent_relation": "What is their relation to you? (e.g., Husband, Father-in-law, Mother-in-law)",
    "respondent_address": "What is the respondent's current address?",
    "nature_of_violence": "What type of violence have you experienced? (Physical / Sexual / Verbal / Emotional / Economic / Dowry harassment)",
    "incident_date": "When did the most recent incident occur? (date or approximate time)",
    "incident_description": "Please describe the incident(s) in your own words.",
    "witnesses": "Are there any witnesses to the violence? If yes, please provide their names and contact.",
    "relief_monetary_amount": "Are you seeking monetary relief? If yes, what amount do you need for medical expenses, rent, or maintenance?",
}

_DIVORCE_QUESTIONS = {
    "petitioner1_name": "What is the full name of the first petitioner (Husband)?",
    "petitioner1_age": "What is the age of the first petitioner?",
    "petitioner1_address": "What is the current address of the first petitioner?",
    "petitioner1_occupation": "What is the occupation of the first petitioner?",
    "petitioner2_name": "What is the full name of the second petitioner (Wife)?",
    "petitioner2_age": "What is the age of the second petitioner?",
    "petitioner2_address": "What is the current address of the second petitioner?",
    "petitioner2_occupation": "What is the occupation of the second petitioner?",
    "marriage_date": "When were you married? (date)",
    "marriage_place": "Where were you married? (city/town)",
    "marriage_registration_number": "Do you have a marriage registration number? (Leave blank if unknown)",
    "separation_date": "When did you start living separately?",
    "separation_address": "Where is each petitioner currently living?",
    "alimony_amount": "Have you agreed on an alimony/maintenance amount? If yes, how much?",
    "alimony_terms": "What are the payment terms for alimony? (e.g., Rs. 5000/month, or one-time settlement)",
    "custody_arrangement": "What is the agreed child custody arrangement?",
    "stridhan_settled": "Has the stridhan (jewellery, gifts) been returned/settled? (Yes/No/Not Applicable)",
    "property_settled": "Has any jointly-held immovable property been divided/settled? (Yes/No/Not Applicable)",
}


def _get_missing(data: dict, intent: str) -> tuple[list[str], list[str]]:
    """Return (missing_field_names, missing_questions) for fields that are null."""
    q_map = {
        "RTI": _RTI_QUESTIONS,
        "Domestic Violence": _DV_QUESTIONS,
        "Divorce": _DIVORCE_QUESTIONS,
    }.get(intent, {})

    missing_fields = []
    missing_questions = []
    for field, question in q_map.items():
        val = data.get(field)
        if val is None or (isinstance(val, list) and len(val) == 0):
            missing_fields.append(field)
            missing_questions.append(question)
    return missing_fields, missing_questions


# ---------------------------------------------------------------------------
# Groq — LLM Analysis
# ---------------------------------------------------------------------------


SYSTEM_PROMPT = """You are Nyaya, an expert Indian legal information assistant specialising in RTI, Domestic Violence, and Divorce law.

LANGUAGE RULE (CRITICAL -- FOLLOW FIRST):
Detect the language the user wrote or spoke in. Respond in THAT SAME LANGUAGE for all text fields:
simplified_explanation, immediate_action_steps, extracted_user_issue, follow_up_question.
Examples: Tamil query -> Tamil response. Hindi query -> Hindi. Telugu, Kannada, Bengali,
Malayalam, Marathi, Gujarati, Punjabi, Odia -> respond in that exact language.
EXCEPTION: The 'relevant_acts' field MUST ALWAYS be in English (legal section numbers are official English terms).
The 'intent_detected' value MUST ALWAYS be: RTI | Domestic Violence | Divorce | Unknown (English).

YOUR CORE MISSION: Give SPECIFIC, DETAILED, LEGALLY PRECISE answers — not generic ones. A generic answer is a failed answer.

RULES FOR EVERY RESPONSE:
1. Always cite SPECIFIC act names, section numbers, and sub-sections from the context provided. Never say "the law" — say "Section 6(1) of the RTI Act, 2005".
2. Tailor every action step to what this specific user said. If they mentioned a government department, name it. If they mentioned physical abuse, cite Section 3 PWDVA and Section 498A IPC specifically.
3. Include fees, timelines, and exact authorities (e.g., "file with the Central Information Commission" not "file an appeal").
4. The follow_up_question field MUST contain one specific question that would help you give an even more precise answer.
5. The relevant_acts field MUST list 3-5 specific sections with brief descriptions.

WHAT YOU MUST ANSWER (kill_switch_triggered = false):
- RTI filing, RTI appeals, RTI exemptions, RTI fees → use the RTI context provided
- Domestic violence, abuse, beating, harassment, dowry harassment → use the PWDVA context provided
- Divorce, separation, alimony, custody → use the HMA context provided

ONLY SET kill_switch_triggered = true when:
- User asks "Should I...?" or "Is it worth...?" (purely subjective opinion)
- Topic is completely outside RTI/DV/Divorce (income tax, criminal theft, property purchase disputes)

Always respond with ONLY a valid JSON object — no markdown, no code fences, no extra text.

JSON schema:
{
  "intent_detected": "RTI | Domestic Violence | Divorce | Unknown",
  "kill_switch_triggered": true | false,
  "simplified_explanation": "string — specific, cites act sections, max 4 sentences",
  "relevant_acts": ["Section X, Act Name — brief description", ...],
  "immediate_action_steps": ["specific step 1", "specific step 2", ...],
  "extracted_user_issue": "string — one sentence, specific to user's words",
  "follow_up_question": "string — one clarifying question, or empty string"
}"""


async def _call_groq_analyze(text: str) -> IntentResult:
    """
    Web-first, RAG-fallback context pipeline:
      1. Run ChromaDB semantic search to get top-3 relevant legal chunks
         AND detect the dominant intent (from the top chunk's topic).
      2. Concurrently attempt a live web fetch from official government portals
         for that intent.
      3. Fuse web content + RAG chunks as context for the LLM.
         - If web fetch succeeds  → context_source = "WEB+RAG"
         - If web fetch fails     → context_source = "RAG"  (pure fallback)
      4. Call Groq Llama 3.3-70b with the fused context.
    """
    # ── Step 1: Semantic retrieval (fast, in-process) ─────────────────────
    rag_context = semantic_retrieve(text, n_results=3)

    # Peek at the top chunk's topic to choose which portal to hit
    top_results = _collection.query(
        query_texts=[text],
        n_results=1,
        include=["metadatas"],
    )
    dominant_intent: str = "RTI"  # default
    if top_results["metadatas"] and top_results["metadatas"][0]:
        dominant_intent = top_results["metadatas"][0][0].get("topic", "RTI")

    # ── Step 2: Live government portal fetch (async, with timeout) ────────
    web_context, sources_used = await fetch_government_context(dominant_intent)

    # ── Step 3: Fuse contexts ─────────────────────────────────────────────
    if web_context and len(web_context) >= 300:
        context_source = "WEB+RAG"
        fused_context = (
            "=== LIVE DATA FROM OFFICIAL GOVERNMENT PORTALS ===\n"
            f"{web_context}\n\n"
            "=== ADDITIONAL CONTEXT FROM LEGAL KNOWLEDGE BASE ===\n"
            f"{rag_context}"
        )
    else:
        context_source = "RAG"
        sources_used = []
        fused_context = (
            "=== CONTEXT FROM LEGAL KNOWLEDGE BASE ===\n"
            f"{rag_context}"
        )

    # ── Step 4: LLM call (sync Groq SDK, run in thread to not block event loop) ──
    prompt = (
        f'User\'s statement (translated to English): "{text}"\n\n'
        f"Context (priority: use government portal data first if available):\n"
        f"{fused_context}\n\n"
        f"Produce a specific, legally precise JSON response for this user's exact situation."
    )

    response = await asyncio.to_thread(
        groq_client.chat.completions.create,
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    raw = response.choices[0].message.content
    data = json.loads(raw)

    # Inject pipeline metadata (not part of LLM output)
    data["context_source"] = context_source
    data["sources_used"] = sources_used

    return IntentResult(**data)


# ---------------------------------------------------------------------------
# PDF builder
# ---------------------------------------------------------------------------


def _build_pdf(data: GeneratePdfRequest, pdf_path: Path) -> None:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Header bar
    pdf.set_fill_color(30, 58, 138)
    pdf.rect(0, 0, 210, 28, "F")
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(10, 8)
    pdf.cell(0, 12, "PROJECT NYAYA — Legal Triage Document", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_xy(10, 20)
    pdf.cell(0, 6, "This document is for informational purposes only. It is NOT legal advice.", ln=True)

    # Intent badge
    pdf.set_text_color(30, 58, 138)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_xy(10, 34)
    pdf.cell(0, 8, f"Detected Intent: {data.intent_detected.upper()}", ln=True)

    pdf.set_draw_color(203, 213, 225)
    pdf.line(10, 44, 200, 44)

    # User issue
    pdf.set_text_color(30, 41, 59)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_xy(10, 48)
    pdf.cell(0, 7, "Summary of Your Issue:", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_xy(10, 56)
    pdf.multi_cell(190, 6, data.extracted_user_issue)

    # Explanation
    y = pdf.get_y() + 4
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_xy(10, y)
    pdf.cell(0, 7, "What This Means:", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_xy(10, pdf.get_y())
    pdf.multi_cell(190, 6, data.simplified_explanation)

    # Relevant Acts
    if data.relevant_acts:
        y = pdf.get_y() + 4
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_xy(10, y)
        pdf.cell(0, 7, "Applicable Laws and Sections:", ln=True)
        pdf.set_font("Helvetica", "", 9)
        for act in data.relevant_acts:
            pdf.set_xy(10, pdf.get_y())
            pdf.multi_cell(190, 6, f"  \u00a7 {act}")

    # Action steps
    y = pdf.get_y() + 4
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_xy(10, y)
    pdf.cell(0, 7, "Immediate Action Steps:", ln=True)
    pdf.set_font("Helvetica", "", 10)
    for i, step in enumerate(data.immediate_action_steps, 1):
        pdf.set_xy(10, pdf.get_y())
        pdf.multi_cell(190, 6, f"  {i}. {step}")

    # Follow-up question
    if data.follow_up_question:
        y = pdf.get_y() + 4
        pdf.set_fill_color(255, 249, 219)
        pdf.set_draw_color(180, 140, 0)
        pdf.set_text_color(120, 80, 0)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_xy(10, y)
        pdf.multi_cell(190, 6, f"  Clarifying Question: {data.follow_up_question}", border=1, fill=True)

    # Kill-switch warning
    if data.kill_switch_triggered:
        y = pdf.get_y() + 6
        pdf.set_fill_color(254, 226, 226)
        pdf.set_draw_color(220, 38, 38)
        pdf.set_text_color(153, 27, 27)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_xy(10, y)
        pdf.multi_cell(
            190, 7,
            "WARNING: This query is outside the scope of this system. "
            "Please consult a qualified legal aid advocate.",
            border=1, fill=True,
        )

    # Footer
    pdf.set_text_color(100, 116, 139)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_xy(10, 280)
    pdf.cell(0, 5, "Generated by Project Nyaya | Not a substitute for professional legal counsel", align="C")
    pdf.output(str(pdf_path))


# ---------------------------------------------------------------------------
# Route 1 — /api/transcribe
# ---------------------------------------------------------------------------


@app.post("/api/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    """Accept audio blob → Groq Whisper-large-v3 → English transcript."""
    suffix = Path(audio.filename or "audio.webm").suffix or ".webm"
    tmp_path = Path(tempfile.mktemp(suffix=suffix))
    try:
        tmp_path.write_bytes(await audio.read())
        with open(tmp_path, "rb") as f:
            response = groq_client.audio.translations.create(
                file=(tmp_path.name, f.read()),
                model="whisper-large-v3",
                response_format="text",
            )
        return {"text": str(response).strip()}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Groq transcription error: {exc}") from exc
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


# ---------------------------------------------------------------------------
# Route 2 — /api/analyze
# ---------------------------------------------------------------------------


@app.post("/api/analyze", response_model=IntentResult)
async def analyze(request: AnalyzeRequest):
    """Text → semantic retrieval → Groq Llama 3.3 → structured IntentResult."""
    try:
        return await _call_groq_analyze(request.text)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"JSON parse error: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Groq analysis error: {exc}") from exc


# ---------------------------------------------------------------------------
# Route 3 — /api/generate_pdf
# ---------------------------------------------------------------------------


@app.post("/api/generate_pdf")
async def generate_pdf(request: GeneratePdfRequest):
    pdf_id = uuid.uuid4().hex
    pdf_filename = f"nyaya_{pdf_id}.pdf"
    _build_pdf(request, STATIC_DIR / pdf_filename)
    return {"pdf_url": f"/static/{pdf_filename}", "pdf_filename": pdf_filename}


# ---------------------------------------------------------------------------
# Route 4 — /api/process  (Master chain)
# ---------------------------------------------------------------------------


@app.post("/api/process")
async def process(audio: UploadFile = File(...)):
    """
    Full pipeline: audio → Whisper → semantic retrieval → Llama analysis → PDF.
    Set DEMO_MODE=true in .env to bypass all API calls.
    """
    # ── DEMO SHORT-CIRCUIT ─────────────────────────────────────────────────
    if DEMO_MODE:
        size = len(await audio.read())
        demo = _demo_process("RTI" if size < 20000 else "Domestic Violence" if size < 60000 else "Divorce")
        pdf_id = uuid.uuid4().hex
        pdf_filename = f"nyaya_{pdf_id}.pdf"
        _build_pdf(
            GeneratePdfRequest(**{k: v for k, v in demo.items() if k != "transcribed_text"}),
            STATIC_DIR / pdf_filename,
        )
        return JSONResponse({**demo, "pdf_url": f"/static/{pdf_filename}"})
    # ── END DEMO ───────────────────────────────────────────────────────────

    # Step 1 — Transcribe
    suffix = Path(audio.filename or "audio.webm").suffix or ".webm"
    tmp_path = Path(tempfile.mktemp(suffix=suffix))
    try:
        tmp_path.write_bytes(await audio.read())
        with open(tmp_path, "rb") as f:
            whisper_resp = groq_client.audio.translations.create(
                file=(tmp_path.name, f.read()),
                model="whisper-large-v3",
                response_format="text",
            )
        text = str(whisper_resp).strip()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Groq transcription error: {exc}") from exc
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

    # Step 2 — Semantic retrieve + Analyze
    try:
        result = await _call_groq_analyze(text)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"JSON parse error: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Groq analysis error: {exc}") from exc

    # Step 3 — PDF
    pdf_id = uuid.uuid4().hex
    pdf_filename = f"nyaya_{pdf_id}.pdf"
    _build_pdf(GeneratePdfRequest(**result.model_dump()), STATIC_DIR / pdf_filename)

    return JSONResponse({
        **result.model_dump(),
        "transcribed_text": text,
        "pdf_url": f"/static/{pdf_filename}",
    })


# ---------------------------------------------------------------------------
# Debug endpoint — inspect retrieved chunks for a given query
# ---------------------------------------------------------------------------


@app.get("/api/debug/retrieve")
async def debug_retrieve(q: str, n: int = 4):
    """
    GET /api/debug/retrieve?q=my+husband+beats+me&n=4
    Shows which legal chunks were semantically matched for a query.
    Useful for testing and tuning retrieval quality.
    """
    results = _collection.query(
        query_texts=[q],
        n_results=n,
        include=["documents", "metadatas", "distances"],
    )
    return {
        "query": q,
        "retrieved": [
            {
                "rank": i + 1,
                "topic": meta["topic"],
                "section": meta["section"],
                "distance": round(dist, 4),
                "preview": doc[:200] + "...",
            }
            for i, (doc, meta, dist) in enumerate(zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            ))
        ],
    }


@app.get("/api/debug/sources")
async def debug_sources(intent: str = None):
    """
    GET /api/debug/sources              → all intents
    GET /api/debug/sources?intent=RTI   → specific intent
    Shows all configured government portal URLs and which sources are tried per intent.
    """
    if intent:
        sources = GOVERNMENT_SOURCES.get(intent, [])
        return {
            "intent": intent,
            "configured_sources": [
                {"url": s["url"], "label": s["label"]} for s in sources
            ],
        }
    return {
        "all_sources": {
            topic: [{"url": s["url"], "label": s["label"]} for s in srcs]
            for topic, srcs in GOVERNMENT_SOURCES.items()
        }
    }


# ---------------------------------------------------------------------------
# Route 6 — /api/extract_form  (AI field extraction from voice text)
# ---------------------------------------------------------------------------


@app.post("/api/extract_form", response_model=FormExtractResponse)
async def extract_form(request: FormExtractRequest):
    """
    Takes the user's transcribed voice text + detected intent.
    Uses Groq Llama to extract every form field it can find.
    Returns: extracted fields (nulls for missing), and what questions to ask next.
    """
    schema_map = {
        "RTI": _RTI_SCHEMA,
        "Domestic Violence": _DV_SCHEMA,
        "Divorce": _DIVORCE_SCHEMA,
    }
    schema = schema_map.get(request.intent, _RTI_SCHEMA)
    prompt = (
        FORM_EXTRACT_PROMPT
        .replace("__SCHEMA__", schema)
        .replace("__TEXT__", request.text)
    )

    try:
        response = await asyncio.to_thread(
            groq_client.chat.completions.create,
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        form_data = json.loads(response.choices[0].message.content)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Form extraction error: {exc}") from exc

    missing_fields, missing_questions = _get_missing(form_data, request.intent)

    return FormExtractResponse(
        intent=request.intent,
        form_data=form_data,
        missing_fields=missing_fields,
        missing_questions=missing_questions,
    )


# ---------------------------------------------------------------------------
# Route 7 — /api/generate_form_pdf  (build filled legal document PDF)
# ---------------------------------------------------------------------------


@app.post("/api/generate_form_pdf")
async def generate_form_pdf(request: dict):
    """
    Takes { intent: str, form_data: dict } and generates a filled PDF.
    Returns { pdf_url, pdf_filename }.
    """
    intent = request.get("intent", "RTI")
    form_data = request.get("form_data", {})

    pdf_id = uuid.uuid4().hex
    pdf_filename = f"nyaya_form_{pdf_id}.pdf"
    pdf_path = STATIC_DIR / pdf_filename

    try:
        if intent == "RTI":
            build_rti_pdf(form_data, pdf_path)
        elif intent == "Domestic Violence":
            build_dv_pdf(form_data, pdf_path)
        elif intent == "Divorce":
            build_divorce_pdf(form_data, pdf_path)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown intent: {intent}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PDF generation error: {exc}") from exc

    return {
        "pdf_url": f"/static/{pdf_filename}",
        "pdf_filename": pdf_filename,
        "intent": intent,
    }
