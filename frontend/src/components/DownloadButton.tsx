"use client";

import { Download } from "lucide-react";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

interface DownloadButtonProps {
  pdfUrl: string;
}

export default function DownloadButton({ pdfUrl }: DownloadButtonProps) {
  const fullUrl = pdfUrl.startsWith("http") ? pdfUrl : `${BACKEND_URL}${pdfUrl}`;

  return (
    <a
      href={fullUrl}
      target="_blank"
      rel="noopener noreferrer"
      download
      className="
        flex items-center justify-center gap-3 w-full
        bg-gradient-to-r from-emerald-500 to-teal-600
        hover:from-emerald-400 hover:to-teal-500
        text-white font-semibold text-base
        rounded-2xl py-4 px-6 shadow-lg shadow-emerald-200
        transition-all duration-300 hover:scale-[1.02] hover:shadow-xl
        focus:outline-none focus:ring-4 focus:ring-emerald-300 focus:ring-offset-2
      "
    >
      <Download className="w-5 h-5 flex-shrink-0" />
      Download Official Document (PDF)
    </a>
  );
}
