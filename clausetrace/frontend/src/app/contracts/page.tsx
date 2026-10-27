"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  FileText,
  Plus,
  ArrowRight,
  ShieldCheck,
  Clock,
  Building,
  AlertCircle,
  UploadCloud,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/utils";

export default function ContractsListPage() {
  const [contracts, setContracts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // New Contract Modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newVendor, setNewVendor] = useState("");
  const [newType, setNewType] = useState("MSA");
  const [newDesc, setNewDesc] = useState("");
  const [creating, setCreating] = useState(false);

  const fetchContracts = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getContracts();
      setContracts(data);
    } catch (err: any) {
      setError(err.message || "Failed to fetch contracts");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchContracts();
    window.addEventListener("clausetrace_user_changed", fetchContracts);
    return () => window.removeEventListener("clausetrace_user_changed", fetchContracts);
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim() || !newVendor.trim()) return;

    try {
      setCreating(true);
      await api.createContract({
        title: newTitle.trim(),
        vendor_name: newVendor.trim(),
        contract_type: newType,
        description: newDesc.trim() || undefined,
      });
      setModalOpen(false);
      setNewTitle("");
      setNewVendor("");
      setNewDesc("");
      await fetchContracts();
    } catch (err: any) {
      alert(`Error creating contract: ${err.message}`);
    } finally {
      setCreating(false);
    }
  };

  const getStatusBadge = (status?: string) => {
    switch (status) {
      case "APPROVED":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700 border border-emerald-200">
            <CheckCircle2 className="h-3.5 w-3.5" /> Approved
          </span>
        );
      case "REJECTED":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-red-50 px-2.5 py-1 text-xs font-semibold text-red-700 border border-red-200">
            <XCircle className="h-3.5 w-3.5" /> Rejected
          </span>
        );
      case "IN_REVIEW":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-700 border border-amber-200">
            <Clock className="h-3.5 w-3.5" /> In Review
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700 border border-slate-200">
            <Clock className="h-3.5 w-3.5" /> Draft
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Contract Agreements</h1>
          <p className="mt-1 text-sm text-slate-500">
            All vendor agreements, immutable versions, and legal sign-off states.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setModalOpen(true)}
            className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3.5 py-2 text-xs font-semibold text-white shadow-sm hover:bg-indigo-700 transition"
          >
            <Plus className="h-4 w-4" />
            New Agreement
          </button>
          <Link
            href="/upload"
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 shadow-sm hover:bg-slate-50 transition"
          >
            <UploadCloud className="h-4 w-4" />
            Upload File
          </Link>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-xs text-red-800">
          {error}
        </div>
      )}

      {loading ? (
        <div className="py-12 text-center text-sm text-slate-500">Loading contracts…</div>
      ) : contracts.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 bg-white p-12 text-center">
          <FileText className="mx-auto h-12 w-12 text-slate-400" />
          <h3 className="mt-2 text-sm font-semibold text-slate-900">No contracts found</h3>
          <p className="mt-1 text-xs text-slate-500">Create your first contract container or upload a file.</p>
          <div className="mt-6 flex justify-center gap-3">
            <button
              onClick={() => setModalOpen(true)}
              className="rounded-lg bg-indigo-600 px-3 py-2 text-xs font-semibold text-white shadow-sm hover:bg-indigo-700"
            >
              Create Agreement
            </button>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {contracts.map((contract) => (
            <Link
              key={contract.id}
              href={`/contracts/${contract.id}`}
              className="group rounded-xl border border-slate-200 bg-white p-5 shadow-sm hover:border-indigo-400 hover:shadow-md transition flex flex-col justify-between"
            >
              <div>
                <div className="flex items-start justify-between gap-2">
                  <span className="rounded bg-indigo-50 text-indigo-700 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider border border-indigo-100">
                    {contract.contract_type}
                  </span>
                  {getStatusBadge(contract.latest_status)}
                </div>

                <h3 className="mt-3 text-base font-bold text-slate-900 group-hover:text-indigo-600 transition">
                  {contract.title}
                </h3>
                <div className="mt-1.5 flex items-center gap-1.5 text-xs text-slate-500">
                  <Building className="h-3.5 w-3.5 text-slate-400" />
                  <span className="font-medium text-slate-700">{contract.vendor_name}</span>
                </div>

                {contract.description && (
                  <p className="mt-2.5 text-xs text-slate-500 line-clamp-2">{contract.description}</p>
                )}
              </div>

              <div className="mt-5 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-400">
                <span>
                  Latest: <strong className="text-slate-700">v{contract.latest_version ?? 1}</strong>
                </span>
                <span className="flex items-center gap-1 font-semibold text-indigo-600 group-hover:translate-x-0.5 transition">
                  View Workspace <ArrowRight className="h-3.5 w-3.5" />
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}

      {/* Modal: Create Agreement */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl border border-slate-200">
            <h2 className="text-lg font-bold text-slate-900">Create New Agreement</h2>
            <p className="text-xs text-slate-500 mt-1">
              Create the agreement container before uploading successive immutable versions.
            </p>

            <form onSubmit={handleCreate} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Agreement Title</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Master Cloud Services Agreement"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-xs focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Vendor / Counterparty</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Acme Cloud Corp"
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
                  <option value="MSA">Master Services Agreement (MSA)</option>
                  <option value="SOW">Statement of Work (SOW)</option>
                  <option value="SLA">Service Level Agreement (SLA)</option>
                  <option value="DPA">Data Processing Agreement (DPA)</option>
                  <option value="NDA">Non-Disclosure Agreement (NDA)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Description (Optional)</label>
                <textarea
                  rows={2}
                  placeholder="Brief context regarding scope or governance..."
                  value={newDesc}
                  onChange={(e) => setNewDesc(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-xs focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div className="mt-6 flex justify-end gap-2.5">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="rounded-lg border border-slate-300 px-3.5 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white shadow-sm hover:bg-indigo-700 disabled:opacity-50"
                >
                  {creating ? "Creating…" : "Create Agreement"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
