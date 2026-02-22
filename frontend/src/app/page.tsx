"use client";

import { useState } from "react";
import MicButton from "@/components/MicButton";
import ResultCard from "@/components/ResultCard";
import Timeline from "@/components/Timeline";
import DownloadButton from "@/components/DownloadButton";
import FormCollector from "@/components/FormCollector";
import { Scale } from "lucide-react";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

interface NyayaResult {
  intent_detected: string;
  kill_switch_triggered: boolean;
  simplified_explanation: string;
  relevant_acts: string[];
  immediate_action_steps: string[];
  extracted_user_issue: string;
  follow_up_question: string;
  transcribed_text: string;
  pdf_url: string;
  context_source?: string;
  sources_used?: string[];
}

export default function Home() {
  const [result, setResult] = useState<NyayaResult | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [inputMode, setInputMode] = useState<"text" | "mic">("text");
  const [textInput, setTextInput] = useState("");
  const [textLoading, setTextLoading] = useState(false);

  const handleResult = (data: NyayaResult) => {
    setErrorMsg(null);
    setResult(data);
    setShowForm(false);
  };

  const handleError = (msg: string) => setErrorMsg(msg);

  const handleReset = () => {
    setResult(null);
    setErrorMsg(null);
    setShowForm(false);
    setTextInput("");
  };

  const handleTextSubmit = async () => {
    if (!textInput.trim()) return;
    setTextLoading(true);
    setErrorMsg(null);
    try {
      const res = await fetch(`${BACKEND_URL}/api/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: textInput.trim() }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error((err as { detail?: string }).detail ?? `Server error ${res.status}`);
      }
      const data = await res.json();
      handleResult({ ...data, transcribed_text: textInput.trim() });
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : "Analysis failed");
    } finally {
      setTextLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-gradient-to-b from-slate-50 via-blue-50 to-indigo-100 py-8 px-4">
      <div className="max-w-md mx-auto space-y-6">

        {}
        <header className="text-center space-y-2">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-600 to-indigo-700 shadow-lg mb-2">
            <Scale className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight text-slate-900">
            Project <span className="text-indigo-600">Nyaya</span>
          </h1>
          <p className="text-sm text-slate-500 max-w-xs mx-auto leading-relaxed">
            Speak or type your legal concern — get clear, actionable guidance instantly.
          </p>
          {/* <div className="inline-block mt-1 px-3 py-0.5 rounded-full bg-amber-100 text-amber-700 text-xs font-semibold ring-1 ring-amber-200">
            Not legal advice · For information only
          </div> */}
        </header>

        {}
        {!result && (
          <section className="bg-white rounded-3xl shadow-xl border border-slate-100 py-8 px-6 space-y-5">

            {}
            <div className="flex rounded-xl overflow-hidden border border-slate-200 text-sm font-semibold">
              <button
                onClick={() => setInputMode("text")}
                className={`flex-1 py-2.5 transition-colors ${
                  inputMode === "text"
                    ? "bg-indigo-600 text-white"
                    : "bg-white text-slate-500 hover:bg-slate-50"
                }`}
              >
                ✏ Type Issue
              </button>
              <button
                onClick={() => setInputMode("mic")}
                className={`flex-1 py-2.5 transition-colors ${
                  inputMode === "mic"
                    ? "bg-indigo-600 text-white"
                    : "bg-white text-slate-500 hover:bg-slate-50"
                }`}
              >
                🎙 Speak Issue
              </button>
            </div>

            {}
            {inputMode === "text" && (
              <div className="space-y-3">
                <label className="block text-sm font-semibold text-slate-700">
                  Describe your legal situation
                </label>
                <textarea
                  id="legal-issue-input"
                  rows={5}
                  className="w-full border border-slate-200 rounded-xl px-4 py-3 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-400 resize-none"
                  placeholder={
                    "Examples:\n" +
                    "• I want to file an RTI about my pension. My name is Ravi Kumar.\n" +
                    "• My husband is beating me, I need a protection order.\n" +
                    "• My wife and I want a mutual divorce, married in 2019."
                  }
                  value={textInput}
                  onChange={(e) => setTextInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) handleTextSubmit();
                  }}
                />
                <button
                  id="analyze-text-btn"
                  onClick={handleTextSubmit}
                  disabled={textLoading || !textInput.trim()}
                  className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-bold py-3 rounded-xl text-sm transition-colors flex items-center justify-center gap-2"
                >
                  {textLoading ? (
                    <>
                      <span className="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      Analysing…
                    </>
                  ) : (
                    "Analyse My Situation →"
                  )}
                </button>
                <p className="text-xs text-slate-400 text-center">Ctrl + Enter to submit</p>
              </div>
            )}

            {}
            {inputMode === "mic" && (
              <div className="flex flex-col items-center space-y-4">
                <MicButton onResult={handleResult} onError={handleError} />
                <p className="text-xs text-slate-400 text-center">
                  Speak in Hindi, Tamil, Kannada, Telugu, Bengali, or any language.
                  <br />Whisper will translate automatically.
                </p>
              </div>
            )}

            {}
            {errorMsg && (
              <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3">
                <p className="text-sm text-red-600 font-medium">{errorMsg}</p>
              </div>
            )}

            <div className="flex flex-wrap gap-2 justify-center pt-1">
              {["RTI Filing", "Domestic Violence", "Mutual Divorce"].map((tag) => (
                <span key={tag} className="text-xs bg-slate-100 text-slate-500 rounded-full px-3 py-1 font-medium">
                  {tag}
                </span>
              ))}
            </div>
          </section>
        )}

        {}
        {result && (
          <>
            <ResultCard
              intentDetected={result.intent_detected}
              killSwitchTriggered={result.kill_switch_triggered}
              simplifiedExplanation={result.simplified_explanation}
              relevantActs={result.relevant_acts ?? []}
              immediateActionSteps={result.immediate_action_steps}
              extractedUserIssue={result.extracted_user_issue}
              followUpQuestion={result.follow_up_question ?? ""}
              transcribedText={result.transcribed_text}
            />

            {!result.kill_switch_triggered && (
              <Timeline intent={result.intent_detected} />
            )}

            {}
            {!result.kill_switch_triggered && (
              <div className="bg-gradient-to-br from-indigo-900 to-blue-900 rounded-2xl p-5 border border-indigo-700 shadow-lg">
                <div className="flex items-start gap-3">
                  <div className="text-2xl">🤖</div>
                  <div className="flex-1">
                    <h3 className="text-white font-bold text-sm mb-1">
                      Let the Agent Fill the Form for You
                    </h3>
                    <p className="text-indigo-200 text-xs leading-relaxed mb-3">
                      Pre-fills a{" "}
                      <strong className="text-white">
                        {result.intent_detected === "RTI"
                          ? "RTI Application"
                          : result.intent_detected === "Domestic Violence"
                          ? "DV Complaint Letter"
                          : "Divorce Petition Draft"}
                      </strong>{" "}
                      from your statement, asks for missing info, then generates a ready-to-submit PDF.
                    </p>
                    <button
                      id="generate-form-btn"
                      onClick={() => setShowForm(true)}
                      className="w-full bg-white text-indigo-800 font-bold text-sm py-2.5 rounded-xl hover:bg-indigo-50 transition-colors"
                    >
                      Generate My Filled Document →
                    </button>
                  </div>
                </div>
              </div>
            )}

            {}
            {result.context_source && (
              <div className="flex items-center justify-center gap-2 text-xs text-slate-400">
                <span className={`px-2 py-0.5 rounded-full font-semibold ${
                  result.context_source === "WEB+RAG"
                    ? "bg-green-100 text-green-700"
                    : "bg-slate-100 text-slate-600"
                }`}>
                  {result.context_source === "WEB+RAG" ? "🌐 Live Gov Data + AI" : "📚 AI Knowledge Base"}
                </span>
                {result.sources_used && result.sources_used.length > 0 && (
                  <span title={result.sources_used.join("\n")}>
                    {result.sources_used.length} portal{result.sources_used.length > 1 ? "s" : ""} queried
                  </span>
                )}
              </div>
            )}

            {result.pdf_url && <DownloadButton pdfUrl={result.pdf_url} />}

            <button
              onClick={handleReset}
              className="w-full py-3 rounded-2xl text-sm font-semibold text-slate-500 border border-slate-200 bg-white hover:bg-slate-50 transition-colors"
            >
              ← Try Another Issue
            </button>
          </>
        )}

        {}
        <footer className="text-center text-xs text-slate-400 pb-4 space-y-1">
          <p>Project Nyaya is not a law firm and does not provide legal counsel.</p>
          <p>In emergencies: Police <strong>100</strong> · Women Helpline <strong>181</strong></p>
        </footer>
      </div>

      {}
      {showForm && result && (
        <FormCollector
          intent={result.intent_detected}
          transcribedText={result.transcribed_text}
          onClose={() => setShowForm(false)}
        />
      )}
    </main>
  );
}