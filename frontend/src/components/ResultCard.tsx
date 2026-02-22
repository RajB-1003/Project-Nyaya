"use client";

import { AlertTriangle, BookOpen, CheckCircle2, HelpCircle } from "lucide-react";

interface ResultCardProps {
  intentDetected: string;
  killSwitchTriggered: boolean;
  simplifiedExplanation: string;
  relevantActs?: string[];
  immediateActionSteps: string[];
  extractedUserIssue: string;
  followUpQuestion?: string;
  transcribedText?: string;
}

export default function ResultCard({
  intentDetected,
  killSwitchTriggered,
  simplifiedExplanation,
  relevantActs = [],
  immediateActionSteps,
  extractedUserIssue,
  followUpQuestion = "",
  transcribedText,
}: ResultCardProps) {
  const intentColors: Record<string, string> = {
    RTI: "bg-blue-100 text-blue-800 ring-blue-200",
    "Domestic Violence": "bg-rose-100 text-rose-800 ring-rose-200",
    Divorce: "bg-purple-100 text-purple-800 ring-purple-200",
    Unknown: "bg-gray-100 text-gray-700 ring-gray-200",
  };
  const badgeClass = intentColors[intentDetected] ?? intentColors.Unknown;

  return (
    <div className="w-full rounded-2xl bg-white shadow-xl border border-slate-100 overflow-hidden">
      {}
      <div
        className={`h-1.5 w-full ${
          killSwitchTriggered
            ? "bg-gradient-to-r from-red-400 to-rose-500"
            : "bg-gradient-to-r from-blue-500 to-indigo-600"
        }`}
      />

      <div className="p-5 space-y-4">
        {}
        <div className="flex items-center justify-between flex-wrap gap-2">
          <span
            className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold ring-1 ${badgeClass}`}
          >
            {intentDetected}
          </span>
          {transcribedText && (
            <p className="text-xs text-slate-400 italic truncate max-w-[60%]">
              &ldquo;{transcribedText}&rdquo;
            </p>
          )}
        </div>

        {}
        {killSwitchTriggered && (
          <div className="flex items-start gap-3 rounded-xl bg-red-50 border border-red-200 p-4">
            <AlertTriangle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-semibold text-red-700">Outside Scope</p>
              <p className="text-sm text-red-600 mt-0.5">{simplifiedExplanation}</p>
            </div>
          </div>
        )}

        {}
        {!killSwitchTriggered && (
          <>
            {}
            <div className="bg-slate-50 rounded-lg px-4 py-3 border border-slate-100">
              <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-1">
                Your Issue
              </p>
              <p className="text-sm text-slate-600">{extractedUserIssue}</p>
            </div>

            {}
            <div>
              <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-1">
                What This Means
              </p>
              <p className="text-sm text-slate-700 leading-relaxed">{simplifiedExplanation}</p>
            </div>

            {}
            {relevantActs.length > 0 && (
              <div className="rounded-xl bg-indigo-50 border border-indigo-100 p-4">
                <div className="flex items-center gap-2 mb-2">
                  <BookOpen className="w-4 h-4 text-indigo-500 flex-shrink-0" />
                  <p className="text-xs text-indigo-600 font-semibold uppercase tracking-wide">
                    Applicable Laws &amp; Sections
                  </p>
                </div>
                <ul className="space-y-1.5">
                  {relevantActs.map((act, idx) => {
                    const [ref, ...desc] = act.split("—");
                    return (
                      <li key={idx} className="flex items-start gap-2">
                        <span className="mt-0.5 text-indigo-500 font-bold text-xs flex-shrink-0">§</span>
                        <span className="text-xs text-indigo-900">
                          <span className="font-semibold">{ref.trim()}</span>
                          {desc.length > 0 && (
                            <span className="text-indigo-700"> — {desc.join("—").trim()}</span>
                          )}
                        </span>
                      </li>
                    );
                  })}
                </ul>
              </div>
            )}

            {}
            <div>
              <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-2">
                Immediate Action Steps
              </p>
              <ul className="space-y-2">
                {immediateActionSteps.map((step, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0 mt-0.5" />
                    <span className="text-sm text-slate-700">{step}</span>
                  </li>
                ))}
              </ul>
            </div>

            {}
            {followUpQuestion && (
              <div className="flex items-start gap-3 rounded-xl bg-amber-50 border border-amber-200 p-3">
                <HelpCircle className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-xs text-amber-700 font-semibold uppercase tracking-wide mb-0.5">
                    To give you a more precise answer:
                  </p>
                  <p className="text-sm text-amber-800">{followUpQuestion}</p>
                </div>
              </div>
            )}
          </>
        )}

        {}
        {killSwitchTriggered && immediateActionSteps.length > 0 && (
          <ul className="space-y-2 mt-1">
            {immediateActionSteps.map((step, idx) => (
              <li key={idx} className="flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-slate-400 flex-shrink-0 mt-0.5" />
                <span className="text-sm text-slate-600">{step}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}