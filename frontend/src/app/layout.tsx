import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Project Nyaya — Voice-First Legal Triage",
  description:
    "Speak your legal concern in any language and receive clear, actionable information on RTI filings, domestic violence protection, and mutual consent divorce. Not legal advice.",
  keywords: ["legal aid", "RTI", "domestic violence", "divorce", "India", "legal triage"],
  openGraph: {
    title: "Project Nyaya",
    description: "Voice-first legal triage for marginalized communities.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="font-sans antialiased">{children}</body>
    </html>
  );
}
