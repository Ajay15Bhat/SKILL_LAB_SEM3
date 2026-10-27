"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  UploadCloud,
  FileText,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Building,
  ArrowRight,
  Shield,
  Layers,
} from "lucide-react";
import { api } from "@/lib/api";

export default function UploadPage() {
  const router = useRouter();

  const [contracts, setContracts] = useState<any[]>([]);
  const [selectedContractId, setSelectedContractId] = useState<string>("new");

  // New contract form
  const [newTitle, setNewTitle] = useState("");
  const [newVendor, setNewVendor] = useState("");
  const [newType, setNewType] = useState("MSA");
  const [newDesc, setNewDesc] = useState("");

  // File state
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getContracts().then(setContracts).catch(console.error);
  }, []);

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError("Please select a contract document file to upload.");
      return;
    }

    try {
      setUploading(true);
      setError(null);
      setUploadProgress("Validating file and computing checksum…");

      let contractId = selectedContractId;
      if (contractId === "new") {
        if (!newTitle.trim() || !newVendor.trim()) {
          throw new Error("Agreement title and vendor name are required.");
        }
        setUploadProgress("Creating agreement container…");
        const newContract = await api.createContract({
          title: newTitle.trim(),
          vendor_name: newVendor.trim(),
          contract_type: newType,
          description: newDesc.trim() || undefined,
        });
        contractId = newContract.id;
      }

      setUploadProgress("Uploading file to private storage & extracting clauses…");
      const versionResult = await api.uploadVersion(contractId, file);

      setUploadProgress("Document successfully parsed into immutable version!");
      setTimeout(() => {
        router.push(`/contracts/${contractId}`);
      }, 1000);
    } catch (err: any) {
      setError(err.message || "Upload failed");
      setUploadProgress(null);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="border-b border-slate-200 pb-5">
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">Upload Contract Document</h1>
        <p className="mt-1 text-sm text-slate-500">
          Upload PDF, DOCX, or text agreements to create an immutable version with SHA-256 fingerprinting.
        </p>
      </div>

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-xs text-red-800 flex items-center gap-2.5">
          <AlertTriangle className="h-4 w-4 text-red-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {uploadProgress && (
        <div className="rounded-xl border border-indigo-200 bg-indigo-50 p-4 text-xs text-indigo-900 flex items-center gap-2.5">
          <Clock className="h-4 w-4 text-indigo-600 animate-spin shrink-0" />
          <span>{uploadProgress}</span>
        </div>
      )}

      <form onSubmit={handleUpload} className="space-y-6">
        {/* Agreement Selection */}
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm space-y-4">
          <label className="block text-xs font-bold text-slate-900 uppercase tracking-wider">
            1. Target Agreement
          </label>

          <div className="space-y-2">
            <select
              value={selectedContractId}
              onChange={(e) => setSelectedContractId(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-xs focus:border-indigo-500 focus:outline-none bg-white font-medium"
            >
              <option value="new">+ Create a New Agreement Container</option>
              {contracts.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.title} ({c.vendor_name}) — Latest: v{c.latest_version ?? 1}
                </option>
              ))}
            </select>
          </div>

          {selectedContractId === "new" && (
            <div className="pt-3 border-t border-slate-100 space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Agreement Title</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Master Services Agreement (MSA)"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-xs focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Vendor / Counterparty</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. CloudNova Technologies"
                    value={newVendor}
                    onChange={(e) => setNewVendor(e.target.value)}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-xs focus:border-indigo-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Contract Type</label>
                  <select
                    value={newType}
                    onChange={(e) => setNewType(e.target.value)}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-xs focus:border-indigo-500 focus:outline-none bg-white"
                  >
                    <option value="MSA">MSA</option>
                    <option value="SOW">SOW</option>
                    <option value="SLA">SLA</option>
                    <option value="DPA">DPA</option>
                  </select>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Drag and Drop Zone */}
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm space-y-3">
          <label className="block text-xs font-bold text-slate-900 uppercase tracking-wider">
            2. Document File
          </label>

          <div
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleFileDrop}
            className={`rounded-2xl border-2 border-dashed p-8 text-center transition ${
              isDragging
                ? "border-indigo-500 bg-indigo-50/50"
                : file
                ? "border-emerald-500 bg-emerald-50/20"
                : "border-slate-300 bg-slate-50/50 hover:border-slate-400"
            }`}
          >
            {file ? (
              <div className="space-y-2">
                <FileText className="mx-auto h-10 w-10 text-emerald-600" />
                <p className="text-sm font-bold text-slate-900">{file.name}</p>
                <p className="text-xs text-slate-500">{(file.size / 1024).toFixed(1)} KB</p>
                <button
                  type="button"
                  onClick={() => setFile(null)}
                  className="text-xs text-red-600 hover:underline font-semibold"
                >
                  Remove & choose another
                </button>
              </div>
            ) : (
              <div className="space-y-2">
                <UploadCloud className="mx-auto h-10 w-10 text-slate-400" />
                <p className="text-sm font-semibold text-slate-700">
                  Drag and drop your contract document here, or browse
                </p>
                <p className="text-xs text-slate-400">Supports PDF, DOCX, and TXT (Max 50MB)</p>
                <label className="mt-3 inline-block rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 shadow-sm hover:bg-slate-50 cursor-pointer">
                  Browse Files
                  <input
                    type="file"
                    accept=".pdf,.docx,.txt"
                    onChange={(e) => setFile(e.target.files?.[0] || null)}
                    className="hidden"
                  />
                </label>
              </div>
            )}
          </div>
        </div>

        {/* Submit */}
        <button
          type="submit"
          disabled={uploading || !file}
          className="w-full rounded-xl bg-indigo-600 py-3 text-xs font-bold text-white shadow-md hover:bg-indigo-700 disabled:opacity-50 transition flex items-center justify-center gap-2"
        >
          <UploadCloud className="h-4 w-4" />
          {uploading ? "Processing Upload & Parsing Clauses…" : "Upload Contract & Parse Version"}
        </button>
      </form>
    </div>
  );
}
