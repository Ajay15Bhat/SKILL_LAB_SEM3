import "./globals.css";
import type { Metadata } from "next";
import Navbar from "@/components/Navbar";

export const metadata: Metadata = {
  title: "ClauseTrace — Contract Change Impact & Obligation Platform",
  description: "Evidence-grounded contract review and change-impact platform with immutable versioning and audit provenance.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-slate-50 text-slate-900 antialiased min-h-screen flex flex-col">
        <Navbar />
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </main>
        <footer className="border-t border-slate-200 bg-white py-6 text-center text-xs text-slate-500">
          <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
            <p>© 2026 ClauseTrace Enterprise. Evidence-Grounded Contract Intelligence.</p>
            <p className="text-slate-400">Review-Support Engine · Not a substitute for professional legal advice.</p>
          </div>
        </footer>
      </body>
    </html>
  );
}
