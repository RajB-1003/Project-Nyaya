"use client";

import { useRef, useState, useCallback } from "react";

type AppStatus = "idle" | "recording" | "loading";

interface MicButtonProps {
  onResult: (data: {
    intent_detected: string;
    kill_switch_triggered: boolean;
    simplified_explanation: string;
    relevant_acts: string[];
    immediate_action_steps: string[];
    extracted_user_issue: string;
    follow_up_question: string;
    transcribed_text: string;
    pdf_url: string;
  }) => void;
  onError: (msg: string) => void;
}

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

export default function MicButton({ onResult, onError }: MicButtonProps) {
  const [status, setStatus] = useState<AppStatus>("idle");
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : "audio/webm";
      const recorder = new MediaRecorder(stream, { mimeType });
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        setStatus("loading");

        const blob = new Blob(chunksRef.current, { type: mimeType });
        const formData = new FormData();
        formData.append("audio", blob, "recording.webm");

        try {
          const res = await fetch(`${BACKEND_URL}/api/process`, {
            method: "POST",
            body: formData,
          });
          if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: "Server error" }));
            throw new Error(err.detail ?? "Unknown server error");
          }
          const data = await res.json();
          onResult(data);
        } catch (err: unknown) {
          onError(err instanceof Error ? err.message : "Failed to process audio");
        } finally {
          setStatus("idle");
        }
      };

      recorder.start();
      mediaRecorderRef.current = recorder;
      setStatus("recording");
    } catch {
      onError("Microphone access denied. Please allow microphone permission and try again.");
    }
  }, [onResult, onError]);

  const stopRecording = useCallback(() => {
    mediaRecorderRef.current?.stop();
  }, []);

  const handleClick = () => {
    if (status === "idle") startRecording();
    else if (status === "recording") stopRecording();
  };

  return (
    <div className="flex flex-col items-center gap-4">
      <button
        onClick={handleClick}
        disabled={status === "loading"}
        aria-label={
          status === "idle"
            ? "Start Recording"
            : status === "recording"
            ? "Stop Recording"
            : "Processing…"
        }
        className={`
          relative w-28 h-28 rounded-full flex items-center justify-center
          shadow-2xl transition-all duration-300 focus:outline-none focus:ring-4 focus:ring-offset-2
          ${
            status === "idle"
              ? "bg-gradient-to-br from-blue-600 to-indigo-700 hover:from-blue-500 hover:to-indigo-600 focus:ring-blue-400 hover:scale-105"
              : status === "recording"
              ? "bg-gradient-to-br from-red-500 to-rose-700 focus:ring-red-400 scale-110"
              : "bg-gradient-to-br from-slate-400 to-slate-500 cursor-not-allowed"
          }
        `}
      >
        {}
        {status === "recording" && (
          <>
            <span className="absolute inset-0 rounded-full bg-red-400 opacity-40 animate-ping" />
            <span className="absolute inset-2 rounded-full bg-red-400 opacity-20 animate-ping [animation-delay:0.3s]" />
          </>
        )}

        {status === "idle" && (
          <svg xmlns="http://www.w3.org/2000/svg" className="w-12 h-12 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 1a3 3 0 0 1 3 3v8a3 3 0 0 1-6 0V4a3 3 0 0 1 3-3z" />
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 10v2a7 7 0 0 1-14 0v-2M12 19v4m-4 0h8" />
          </svg>
        )}

        {status === "recording" && (
          <svg xmlns="http://www.w3.org/2000/svg" className="w-12 h-12 text-white" fill="currentColor" viewBox="0 0 24 24">
            <rect x="6" y="6" width="12" height="12" rx="2" />
          </svg>
        )}

        {status === "loading" && (
          <svg className="w-12 h-12 text-white animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
        )}
      </button>

      <p className="text-sm font-medium tracking-wide text-slate-500 uppercase">
        {status === "idle" && "Tap to speak"}
        {status === "recording" && "Recording… tap to stop"}
        {status === "loading" && "Analysing your issue…"}
      </p>
    </div>
  );
}