"use client";

import { useState } from "react";

// ─── Types ───────────────────────────────────────────────────────────────────

interface FormCollectorProps {
  intent: string;
  transcribedText: string;
  onClose?: () => void;
}

interface FormExtractResponse {
  intent: string;
  form_data: Record<string, unknown>;
  missing_fields: string[];
  missing_questions: string[];
}

// ─── Field label map (identifier → display name) ─────────────────────────────

const FIELD_LABELS: Record<string, string> = {
  // RTI
  name: "Full Name",
  address: "Complete Address",
  phone: "Phone Number",
  email: "Email Address",
  bpl_status: "BPL Card Holder?",
  department_name: "Government Department Name",
  department_address: "Department Address",
  pio_name: "Public Information Officer (PIO) Name",
  information_requested: "Specific Information Requested",
  time_period: "Time Period of Information",
  format_required: "Format Required",
  fee_payment_mode: "Fee Payment Mode",
  // DV
  complainant_name: "Your Full Name",
  complainant_age: "Your Age",
  complainant_address: "Your Safe Address",
  complainant_phone: "Your Phone",
  respondent_name: "Abuser's Full Name",
  respondent_relation: "Abuser's Relation to You",
  respondent_address: "Abuser's Address",
  nature_of_violence: "Type(s) of Violence",
  incident_date: "Date of Incident",
  incident_description: "Description of Incident",
  witnesses: "Witness Names & Contact",
  children: "Children (Name & Age)",
  relief_monetary_amount: "Monetary Relief Sought (Rs.)",
  // Divorce
  petitioner1_name: "Petitioner 1 Full Name",
  petitioner1_age: "Petitioner 1 Age",
  petitioner1_address: "Petitioner 1 Address",
  petitioner1_occupation: "Petitioner 1 Occupation",
  petitioner2_name: "Petitioner 2 Full Name",
  petitioner2_age: "Petitioner 2 Age",
  petitioner2_address: "Petitioner 2 Address",
  petitioner2_occupation: "Petitioner 2 Occupation",
  marriage_date: "Date of Marriage",
  marriage_place: "Place of Marriage",
  marriage_registration_number: "Marriage Registration No.",
  separation_date: "Date of Separation",
  separation_address: "Address (Living Separately)",
  alimony_amount: "Agreed Alimony / Maintenance",
  alimony_terms: "Alimony Payment Terms",
  custody_arrangement: "Child Custody Arrangement",
  stridhan_settled: "Stridhan / Jewellery Settled?",
  property_settled: "Immovable Property Settled?",
};

const TEXTAREA_FIELDS = new Set([
  "address", "information_requested", "incident_description",
  "complainant_address", "respondent_address", "department_address",
  "separation_address", "petitioner1_address", "petitioner2_address",
]);

const INTENT_TITLES: Record<string, string> = {
  RTI: "RTI Application — Section 6, Right to Information Act 2005",
  "Domestic Violence": "Domestic Violence Complaint — PWDVA 2005",
  Divorce: "Mutual Consent Divorce Petition — Section 13B, HMA 1955",
};

// ─── Component ────────────────────────────────────────────────────────────────

export default function FormCollector({ intent, transcribedText, onClose }: FormCollectorProps) {
  const [step, setStep] = useState<"loading" | "filling" | "generating" | "done">("loading");
  const [formData, setFormData] = useState<Record<string, unknown>>({});
  const [missingFields, setMissingFields] = useState<string[]>([]);
  const [missingQuestions, setMissingQuestions] = useState<string[]>([]);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // ─── Step 1: Extract fields from voice on mount ──────────────────────────

  useState(() => {
    const extract = async () => {
      try {
        const res = await fetch("http://localhost:8000/api/extract_form", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: transcribedText, intent }),
        });
        if (!res.ok) throw new Error(`Server error: ${res.status}`);
        const data: FormExtractResponse = await res.json();
        setFormData(data.form_data);
        setMissingFields(data.missing_fields);
        setMissingQuestions(data.missing_questions);
        setStep("filling");
      } catch (e) {
        setError(e instanceof Error ? e.message : "Extraction failed");
        setStep("filling");
      }
    };
    extract();
  });

  // ─── Step 2: Update field value ──────────────────────────────────────────

  const updateField = (field: string, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  // ─── Step 3: Generate filled PDF ─────────────────────────────────────────

  const generatePdf = async () => {
    setStep("generating");
    try {
      const res = await fetch("http://localhost:8000/api/generate_form_pdf", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ intent, form_data: formData }),
      });
      if (!res.ok) throw new Error(`PDF generation failed: ${res.status}`);
      const data = await res.json();
      setPdfUrl(`http://localhost:8000${data.pdf_url}`);
      setStep("done");
    } catch (e) {
      setError(e instanceof Error ? e.message : "PDF generation failed");
      setStep("filling");
    }
  };

  // ─── Render helpers ───────────────────────────────────────────────────────

  const renderField = (field: string, question: string, isMissing: boolean) => {
    const label = FIELD_LABELS[field] || field;
    const value = (formData[field] as string) || "";
    const isTextarea = TEXTAREA_FIELDS.has(field);

    return (
      <div key={field} className={`form-field ${isMissing ? "missing" : "filled"}`}>
        <label className="field-label">
          {label}
          {isMissing && <span className="required-badge">Required</span>}
          {!isMissing && <span className="filled-badge">✓ Extracted</span>}
        </label>
        {isMissing && (
          <p className="field-question">{question}</p>
        )}
        {isTextarea ? (
          <textarea
            className={`field-input textarea ${isMissing ? "input-missing" : "input-filled"}`}
            value={value}
            onChange={(e) => updateField(field, e.target.value)}
            placeholder={isMissing ? "Type your answer here..." : ""}
            rows={3}
          />
        ) : (
          <input
            type="text"
            className={`field-input ${isMissing ? "input-missing" : "input-filled"}`}
            value={value}
            onChange={(e) => updateField(field, e.target.value)}
            placeholder={isMissing ? "Type your answer here..." : ""}
          />
        )}
      </div>
    );
  };

  // ─── All fields to show (filled first, then missing) ─────────────────────

  const allFilledFields = Object.entries(formData)
    .filter(([k, v]) => {
      if (!FIELD_LABELS[k]) return false;
      if (v === null || v === undefined) return false;
      if (typeof v === "boolean") return false;
      if (Array.isArray(v) && v.length === 0) return false;
      return !missingFields.includes(k);
    });

  // ─── JSX ─────────────────────────────────────────────────────────────────

  return (
    <div className="form-collector-overlay">
      <div className="form-collector-panel">
        {/* Header */}
        <div className="form-header">
          <div>
            <span className="form-badge">{intent}</span>
            <h2 className="form-title">{INTENT_TITLES[intent] || "Legal Document"}</h2>
            <p className="form-subtitle">
              AI pre-filled what it found in your voice statement.
              {missingFields.length > 0
                ? ` Please fill in the ${missingFields.length} remaining field${missingFields.length > 1 ? "s" : ""}.`
                : " All fields extracted — ready to generate."}
            </p>
          </div>
          {onClose && (
            <button className="form-close-btn" onClick={onClose}>✕</button>
          )}
        </div>

        {/* Loading state */}
        {step === "loading" && (
          <div className="form-loading">
            <div className="form-spinner" />
            <p>Analysing your statement and pre-filling the form…</p>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="form-error">
            <strong>Error:</strong> {error}
          </div>
        )}

        {/* Form fields */}
        {(step === "filling" || step === "generating") && (
          <div className="form-fields-container">
            {/* Missing fields section */}
            {missingFields.length > 0 && (
              <div className="fields-section">
                <h3 className="section-title missing-section-title">
                  ⚠ Information Needed ({missingFields.length} field{missingFields.length > 1 ? "s" : ""})
                </h3>
                {missingFields.map((field, i) =>
                  renderField(field, missingQuestions[i] || "", true)
                )}
              </div>
            )}

            {/* Pre-filled fields section */}
            {allFilledFields.length > 0 && (
              <div className="fields-section">
                <h3 className="section-title filled-section-title">
                  ✓ Pre-filled from Your Statement ({allFilledFields.length} field{allFilledFields.length > 1 ? "s" : ""})
                </h3>
                {allFilledFields.map(([field]) =>
                  renderField(field, "", false)
                )}
              </div>
            )}
          </div>
        )}

        {/* Generate button */}
        {(step === "filling" || step === "generating") && (
          <div className="form-actions">
            <button
              className={`generate-btn ${step === "generating" ? "generating" : ""}`}
              onClick={generatePdf}
              disabled={step === "generating"}
            >
              {step === "generating" ? (
                <>
                  <span className="btn-spinner" />
                  Generating Document…
                </>
              ) : (
                "Generate My Legal Document →"
              )}
            </button>
            <p className="form-disclaimer">
              Orange fields are incomplete and will appear as blank lines on the PDF.
            </p>
          </div>
        )}

        {/* Done — PDF ready */}
        {step === "done" && pdfUrl && (
          <div className="form-done">
            <div className="done-icon">📄</div>
            <h3 className="done-title">Your Document is Ready</h3>
            <p className="done-subtitle">
              Review it before filing. Orange sections need to be filled in by hand.
            </p>
            <div className="done-actions">
              <a
                href={pdfUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="download-btn"
              >
                ↓ Download PDF
              </a>
              <button
                className="edit-btn"
                onClick={() => setStep("filling")}
              >
                ← Edit Fields
              </button>
            </div>
            <p className="done-disclaimer">
              This is a draft document prepared with AI assistance. Review with a Legal Aid advocate before filing.
              Free legal aid: <strong>NALSA Helpline 15100</strong>
            </p>
          </div>
        )}
      </div>

      <style jsx>{`
        .form-collector-overlay {
          position: fixed;
          inset: 0;
          background: rgba(0, 0, 0, 0.6);
          backdrop-filter: blur(4px);
          z-index: 100;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 1rem;
        }
        .form-collector-panel {
          background: #0f172a;
          border: 1px solid #1e3a8a;
          border-radius: 16px;
          width: 100%;
          max-width: 720px;
          max-height: 90vh;
          overflow-y: auto;
          display: flex;
          flex-direction: column;
          box-shadow: 0 25px 60px rgba(0, 0, 0, 0.5);
        }
        .form-header {
          background: linear-gradient(135deg, #1e3a8a, #1e40af);
          padding: 1.5rem;
          border-radius: 16px 16px 0 0;
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          gap: 1rem;
        }
        .form-badge {
          background: rgba(255,255,255,0.2);
          color: #fff;
          font-size: 0.7rem;
          font-weight: 700;
          letter-spacing: 0.1em;
          text-transform: uppercase;
          padding: 2px 10px;
          border-radius: 20px;
          margin-bottom: 0.5rem;
          display: inline-block;
        }
        .form-title {
          color: #fff;
          font-size: 1rem;
          font-weight: 700;
          margin: 0.25rem 0;
        }
        .form-subtitle {
          color: #bfdbfe;
          font-size: 0.8rem;
          margin: 0;
        }
        .form-close-btn {
          background: rgba(255,255,255,0.15);
          border: none;
          color: #fff;
          width: 32px;
          height: 32px;
          border-radius: 50%;
          cursor: pointer;
          font-size: 0.9rem;
          flex-shrink: 0;
          transition: background 0.2s;
        }
        .form-close-btn:hover { background: rgba(255,255,255,0.3); }

        .form-loading {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 1rem;
          padding: 3rem;
          color: #94a3b8;
        }
        .form-spinner {
          width: 36px; height: 36px;
          border: 3px solid #1e40af;
          border-top-color: #60a5fa;
          border-radius: 50%;
          animation: spin 0.8s linear infinite;
        }
        .form-error {
          margin: 1rem 1.5rem;
          padding: 0.75rem 1rem;
          background: #450a0a;
          border: 1px solid #b91c1c;
          border-radius: 8px;
          color: #fca5a5;
          font-size: 0.85rem;
        }

        .form-fields-container {
          padding: 1.5rem;
          display: flex;
          flex-direction: column;
          gap: 1.5rem;
        }
        .fields-section { display: flex; flex-direction: column; gap: 0.75rem; }
        .section-title {
          font-size: 0.8rem;
          font-weight: 700;
          letter-spacing: 0.05em;
          padding: 0.5rem 0.75rem;
          border-radius: 6px;
          margin: 0;
        }
        .missing-section-title {
          background: #431407;
          color: #fb923c;
          border-left: 3px solid #f97316;
        }
        .filled-section-title {
          background: #052e16;
          color: #4ade80;
          border-left: 3px solid #22c55e;
        }

        .form-field { display: flex; flex-direction: column; gap: 0.3rem; }
        .field-label {
          font-size: 0.8rem;
          font-weight: 600;
          color: #cbd5e1;
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }
        .required-badge {
          background: #78350f;
          color: #fbbf24;
          font-size: 0.65rem;
          padding: 1px 6px;
          border-radius: 10px;
          font-weight: 700;
        }
        .filled-badge {
          background: #064e3b;
          color: #34d399;
          font-size: 0.65rem;
          padding: 1px 6px;
          border-radius: 10px;
          font-weight: 700;
        }
        .field-question {
          font-size: 0.78rem;
          color: #94a3b8;
          margin: 0;
          font-style: italic;
        }
        .field-input {
          width: 100%;
          padding: 0.5rem 0.75rem;
          border-radius: 8px;
          border: 1.5px solid;
          font-size: 0.85rem;
          font-family: inherit;
          outline: none;
          transition: border-color 0.2s;
          box-sizing: border-box;
        }
        .field-input.textarea { resize: vertical; min-height: 70px; }
        .input-missing {
          background: #1c0d00;
          border-color: #92400e;
          color: #fde68a;
        }
        .input-missing:focus { border-color: #f97316; }
        .input-filled {
          background: #0a1a0a;
          border-color: #166534;
          color: #bbf7d0;
        }
        .input-filled:focus { border-color: #22c55e; }

        .form-actions {
          padding: 1rem 1.5rem 1.5rem;
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
          align-items: stretch;
          border-top: 1px solid #1e293b;
        }
        .generate-btn {
          background: linear-gradient(135deg, #2563eb, #1d4ed8);
          color: #fff;
          border: none;
          border-radius: 10px;
          padding: 0.85rem 1.5rem;
          font-size: 0.95rem;
          font-weight: 700;
          cursor: pointer;
          transition: opacity 0.2s;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 0.5rem;
        }
        .generate-btn:hover:not(:disabled) { opacity: 0.9; }
        .generate-btn:disabled { opacity: 0.6; cursor: not-allowed; }
        .btn-spinner {
          width: 18px; height: 18px;
          border: 2px solid rgba(255,255,255,0.3);
          border-top-color: #fff;
          border-radius: 50%;
          animation: spin 0.8s linear infinite;
        }
        .form-disclaimer {
          font-size: 0.72rem;
          color: #64748b;
          text-align: center;
          margin: 0;
        }

        .form-done {
          padding: 2.5rem 1.5rem;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 0.75rem;
          text-align: center;
        }
        .done-icon { font-size: 2.5rem; }
        .done-title { color: #fff; font-size: 1.2rem; font-weight: 700; margin: 0; }
        .done-subtitle { color: #94a3b8; font-size: 0.85rem; margin: 0; }
        .done-actions { display: flex; gap: 1rem; margin-top: 0.5rem; }
        .download-btn {
          background: linear-gradient(135deg, #2563eb, #1d4ed8);
          color: #fff;
          text-decoration: none;
          border-radius: 10px;
          padding: 0.7rem 1.5rem;
          font-weight: 700;
          font-size: 0.9rem;
          transition: opacity 0.2s;
        }
        .download-btn:hover { opacity: 0.9; }
        .edit-btn {
          background: #1e293b;
          color: #94a3b8;
          border: 1px solid #334155;
          border-radius: 10px;
          padding: 0.7rem 1.2rem;
          font-size: 0.9rem;
          cursor: pointer;
          transition: background 0.2s;
        }
        .edit-btn:hover { background: #273449; }
        .done-disclaimer {
          font-size: 0.75rem;
          color: #64748b;
          max-width: 500px;
          line-height: 1.5;
        }

        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
