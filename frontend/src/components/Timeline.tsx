"use client";

import { TIMELINE_MAP } from "@/data/timelines";
import { CheckCircle2 } from "lucide-react";

interface TimelineProps {
  intent: string;
}

export default function Timeline({ intent }: TimelineProps) {
  const steps =
    TIMELINE_MAP[intent as keyof typeof TIMELINE_MAP] ?? null;

  if (!steps) return null;

  return (
    <div className="w-full rounded-2xl bg-white shadow-xl border border-slate-100 overflow-hidden">
      <div className="h-1 w-full bg-gradient-to-r from-indigo-500 via-blue-400 to-cyan-400" />
      <div className="p-5">
        <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-5">
          Step-by-Step Procedure — {intent}
        </h3>

        <ol className="relative space-y-0">
          {steps.map((step, idx) => {
            const isLast = idx === steps.length - 1;
            return (
              <li key={step.id} className="relative flex gap-4">
                {}
                {!isLast && (
                  <span
                    className="absolute left-5 top-10 bottom-0 w-px bg-indigo-100"
                    aria-hidden="true"
                  />
                )}

                {}
                <div className="flex-shrink-0 w-10 h-10 rounded-full bg-indigo-600 text-white flex items-center justify-center text-sm font-bold shadow-md z-10">
                  {step.id}
                </div>

                {}
                <div className={`pb-6 ${isLast ? "pb-0" : ""}`}>
                  <p className="font-semibold text-slate-800 text-sm leading-snug">
                    {step.title}
                  </p>
                  <p className="text-xs text-slate-500 mt-1 leading-relaxed">
                    {step.description}
                  </p>
                </div>
              </li>
            );
          })}
        </ol>

        {}
        <div className="mt-4 flex items-center gap-2 text-xs text-emerald-600 font-medium bg-emerald-50 rounded-lg px-3 py-2">
          <CheckCircle2 className="w-4 h-4" />
          Follow these steps carefully. Seek a legal aid advocate for personalised guidance.
        </div>
      </div>
    </div>
  );
}