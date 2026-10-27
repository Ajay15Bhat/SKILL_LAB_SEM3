"use client";

import { useEffect, useState } from "react";
import {
  ListTodo,
  Plus,
  Calendar,
  AlertTriangle,
  CheckCircle2,
  Clock,
  User,
  Filter,
  ArrowRight,
  ShieldAlert,
} from "lucide-react";
import { api, getActiveUser } from "@/lib/api";
import { formatShortDate } from "@/lib/utils";

export default function ObligationsPage() {
  const [obligations, setObligations] = useState<any[]>([]);
  const [contracts, setContracts] = useState<any[]>([]);
  const [selectedContractId, setSelectedContractId] = useState<string>("");
  const [versions, setVersions] = useState<any[]>([]);
  const [selectedVersionId, setSelectedVersionId] = useState<string>("");

  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Create Modal
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [party, setParty] = useState("VENDOR");
  const [dueDate, setDueDate] = useState("");
  const [frequency, setFrequency] = useState("ONE_TIME");
  const [creating, setCreating] = useState(false);

  const activeUser = getActiveUser();

  const fetchContracts = async () => {
    try {
      const cList = await api.getContracts();
      setContracts(cList);
      if (cList.length > 0) {
        setSelectedContractId(cList[0].id);
      }
    } catch (err: any) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchContracts();
  }, []);

  useEffect(() => {
    if (!selectedContractId) return;
    api.getContractVersions(selectedContractId).then((vList) => {
      setVersions(vList);
      if (vList.length > 0) {
        setSelectedVersionId(vList[0].id);
      } else {
        setSelectedVersionId("");
      }
    });
  }, [selectedContractId]);

  useEffect(() => {
    fetchObligations();
  }, [selectedVersionId]);

  const fetchObligations = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getObligations(selectedVersionId || undefined);
      setObligations(data);
    } catch (err: any) {
      setError(err.message || "Failed to load obligations");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateObligation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedVersionId || !title.trim() || !description.trim()) return;

    try {
      setCreating(true);
      await api.createObligation({
        contract_version_id: selectedVersionId,
        title: title.trim(),
        description: description.trim(),
        party,
        due_date: dueDate || undefined,
        frequency,
      });
      setCreateModalOpen(false);
      setTitle("");
      setDescription("");
      setDueDate("");
      await fetchObligations();
    } catch (err: any) {
      alert(`Error creating obligation: ${err.message}`);
    } finally {
      setCreating(false);
    }
  };

  const handleUpdateStatus = async (id: string, newStatus: string) => {
    try {
      await api.updateObligation(id, { status: newStatus });
      await fetchObligations();
    } catch (err: any) {
      alert(`Error updating obligation: ${err.message}`);
    }
  };

  const filteredObligations = obligations.filter((o) => {
    if (statusFilter === "ALL") return true;
    if (statusFilter === "OVERDUE") return o.is_overdue || o.status === "OVERDUE";
    return o.status === statusFilter;
  });

  const getStatusBadge = (status: string, isOverdue: boolean) => {
    if (isOverdue || status === "OVERDUE") {
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-bold text-red-800 border border-red-200">
          <AlertTriangle className="h-3.5 w-3.5" /> OVERDUE
        </span>
      );
    }
    switch (status) {
      case "COMPLETED":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-bold text-emerald-800 border border-emerald-200">
            <CheckCircle2 className="h-3.5 w-3.5" /> COMPLETED
          </span>
        );
      case "IN_PROGRESS":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-bold text-blue-800 border border-blue-200">
            <Clock className="h-3.5 w-3.5" /> IN PROGRESS
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-bold text-slate-700 border border-slate-200">
            <Clock className="h-3.5 w-3.5" /> PENDING
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Contractual Obligations & SLAs</h1>
          <p className="mt-1 text-sm text-slate-500">
            Track operational commitments, delivery milestones, and covenants tied to specific contract versions.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <select
            value={selectedContractId}
            onChange={(e) => setSelectedContractId(e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-semibold focus:border-indigo-500 focus:outline-none bg-white shadow-sm"
          >
            {contracts.map((c) => (
              <option key={c.id} value={c.id}>
                {c.title} ({c.vendor_name})
              </option>
            ))}
          </select>

          <select
            value={selectedVersionId}
            onChange={(e) => setSelectedVersionId(e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-semibold focus:border-indigo-500 focus:outline-none bg-white shadow-sm"
          >
            {versions.map((v) => (
              <option key={v.id} value={v.id}>
                v{v.version_number} ({v.approval_status})
              </option>
            ))}
          </select>

          <button
            onClick={() => setCreateModalOpen(true)}
            disabled={!selectedVersionId}
            className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3.5 py-2 text-xs font-semibold text-white shadow-sm hover:bg-indigo-700 disabled:opacity-50"
          >
            <Plus className="h-4 w-4" />
            Add Obligation
          </button>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 text-xs">
        {["ALL", "PENDING", "IN_PROGRESS", "OVERDUE", "COMPLETED"].map((st) => (
          <button
            key={st}
            onClick={() => setStatusFilter(st)}
            className={`rounded-lg px-3 py-1.5 font-semibold transition ${
              statusFilter === st
                ? "bg-indigo-600 text-white shadow-sm"
                : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-50"
            }`}
          >
            {st.replace(/_/g, " ")}
          </button>
        ))}
      </div>

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-xs text-red-800">
          {error}
        </div>
      )}

      {loading ? (
        <div className="py-20 text-center text-sm text-slate-500">Loading obligations…</div>
      ) : filteredObligations.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 bg-white p-12 text-center text-xs text-slate-500">
          No obligations match the current filters. Click &quot;Add Obligation&quot; to assign a contractual commitment.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredObligations.map((ob) => (
            <div
              key={ob.id}
              className={`rounded-2xl border p-5 shadow-sm space-y-3 bg-white transition ${
                ob.is_overdue ? "border-red-300 ring-1 ring-red-100" : "border-slate-200"
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <span className="rounded bg-slate-100 text-slate-700 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider">
                    {ob.party} OBLIGATION
                  </span>
                  <h3 className="text-sm font-bold text-slate-900 mt-1">{ob.title}</h3>
                </div>
                {getStatusBadge(ob.status, ob.is_overdue)}
              </div>

              <p className="text-xs text-slate-600 leading-relaxed">{ob.description}</p>

              <div className="pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
                <div className="flex items-center gap-3">
                  <span className="flex items-center gap-1 font-medium text-slate-700">
                    <Calendar className="h-3.5 w-3.5 text-slate-400" />
                    Due: {formatShortDate(ob.due_date)}
                  </span>
                  <span className="text-[11px] text-slate-400">Freq: {ob.frequency}</span>
                </div>

                {/* State Transition Actions */}
                <div className="flex items-center gap-1.5">
                  {ob.status !== "COMPLETED" && (
                    <button
                      onClick={() => handleUpdateStatus(ob.id, "COMPLETED")}
                      className="rounded bg-emerald-50 px-2.5 py-1 text-[11px] font-bold text-emerald-800 hover:bg-emerald-100 border border-emerald-200"
                    >
                      Mark Complete
                    </button>
                  )}
                  {ob.status === "PENDING" && (
                    <button
                      onClick={() => handleUpdateStatus(ob.id, "IN_PROGRESS")}
                      className="rounded bg-blue-50 px-2.5 py-1 text-[11px] font-bold text-blue-800 hover:bg-blue-100 border border-blue-200"
                    >
                      Start Work
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal: Create Obligation */}
      {createModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl border border-slate-200">
            <h2 className="text-lg font-bold text-slate-900">Add Contractual Obligation</h2>
            <p className="text-xs text-slate-500 mt-1">
              Assigns a compliance milestone or operational covenant to Version {versions.find(v => v.id === selectedVersionId)?.version_number}.
            </p>

            <form onSubmit={handleCreateObligation} className="mt-4 space-y-4 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Obligation Title</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Quarterly SOC2 Type II Audit Delivery"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Detailed Commitment Scope</label>
                <textarea
                  rows={3}
                  required
                  placeholder="Vendor shall provide audited report by the 15th of the following month..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Responsible Party</label>
                  <select
                    value={party}
                    onChange={(e) => setParty(e.target.value)}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-indigo-500 focus:outline-none bg-white font-medium"
                  >
                    <option value="VENDOR">Vendor</option>
                    <option value="CUSTOMER">Customer</option>
                    <option value="MUTUAL">Mutual</option>
                  </select>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Frequency</label>
                  <select
                    value={frequency}
                    onChange={(e) => setFrequency(e.target.value)}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-indigo-500 focus:outline-none bg-white font-medium"
                  >
                    <option value="ONE_TIME">One-Time</option>
                    <option value="MONTHLY">Monthly</option>
                    <option value="QUARTERLY">Quarterly</option>
                    <option value="ANNUAL">Annual</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Due Date</label>
                <input
                  type="date"
                  value={dueDate}
                  onChange={(e) => setDueDate(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-indigo-500 focus:outline-none bg-white font-medium"
                />
              </div>

              <div className="mt-6 flex justify-end gap-2.5">
                <button
                  type="button"
                  onClick={() => setCreateModalOpen(false)}
                  className="rounded-lg border border-slate-300 px-3.5 py-2 font-semibold text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="rounded-lg bg-indigo-600 px-4 py-2 font-semibold text-white shadow-sm hover:bg-indigo-700 disabled:opacity-50"
                >
                  {creating ? "Saving…" : "Save Obligation"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
