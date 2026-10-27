"use client";

import { useEffect, useState } from "react";
import {
  CheckCircle2,
  AlertTriangle,
  Clock,
  XCircle,
  FileText,
  Filter,
  Check,
  RotateCcw,
  ShieldAlert,
  ArrowRight,
  UserCheck,
} from "lucide-react";
import { api, getActiveUser } from "@/lib/api";
import { formatDate } from "@/lib/utils";

export default function ReviewsPage() {
  const [contracts, setContracts] = useState<any[]>([]);
  const [selectedContractId, setSelectedContractId] = useState<string>("");
  const [versions, setVersions] = useState<any[]>([]);
  const [selectedVersionId, setSelectedVersionId] = useState<string>("");

  const [findings, setFindings] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Decision Modal
  const [decisionModalOpen, setDecisionModalOpen] = useState(false);
  const [activeFinding, setActiveFinding] = useState<any>(null);
  const [decisionType, setDecisionType] = useState<"CONFIRMED" | "OVERRIDDEN">("CONFIRMED");
  const [overriddenStatus, setOverriddenStatus] = useState<string>("SATISFIED");
  const [overrideReason, setOverrideReason] = useState("");
  const [submittingDecision, setSubmittingDecision] = useState(false);

  const activeUser = getActiveUser();

  useEffect(() => {
    api.getContracts().then((cList) => {
      setContracts(cList);
      if (cList.length > 0) {
        setSelectedContractId(cList[0].id);
      }
    });
  }, []);

  useEffect(() => {
    if (!selectedContractId) return;
    api.getContractVersions(selectedContractId).then((vList) => {
      setVersions(vList);
      if (vList.length > 0) {
        setSelectedVersionId(vList[0].id);
      } else {
        setSelectedVersionId("");
        setFindings([]);
      }
    });
  }, [selectedContractId]);

  useEffect(() => {
    if (!selectedVersionId) return;
    fetchFindings();
  }, [selectedVersionId]);

  const fetchFindings = async () => {
    if (!selectedVersionId) return;
    try {
      setLoading(true);
      setError(null);
      const data = await api.getFindings({ version_id: selectedVersionId });
      setFindings(data);
    } catch (err: any) {
      setError(err.message || "Failed to load findings");
    } finally {
      setLoading(false);
    }
  };

  const handleOpenDecisionModal = (f: any, type: "CONFIRMED" | "OVERRIDDEN") => {
    setActiveFinding(f);
    setDecisionType(type);
    setOverriddenStatus(f.status === "SATISFIED" ? "NEEDS_REVIEW" : "SATISFIED");
    setOverrideReason("");
    setDecisionModalOpen(true);
  };

  const handleSubmitDecision = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeFinding) return;

    try {
      setSubmittingDecision(true);
      await api.updateFindingDecision(
        activeFinding.id,
        decisionType,
        decisionType === "OVERRIDDEN" ? overriddenStatus : undefined,
        decisionType === "OVERRIDDEN" ? overrideReason : undefined
      );
      setDecisionModalOpen(false);
      await fetchFindings();
    } catch (err: any) {
      alert(`Failed to record decision: ${err.message}`);
    } finally {
      setSubmittingDecision(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "SATISFIED":
        return <span className="rounded bg-emerald-100 text-emerald-800 px-2.5 py-1 text-xs font-bold border border-emerald-200">SATISFIED</span>;
      case "NOT_SATISFIED":
        return <span className="rounded bg-red-100 text-red-800 px-2.5 py-1 text-xs font-bold border border-red-200">NOT SATISFIED</span>;
      case "PARTIALLY_SATISFIED":
        return <span className="rounded bg-amber-100 text-amber-800 px-2.5 py-1 text-xs font-bold border border-amber-200">PARTIAL</span>;
      case "NOT_FOUND":
        return <span className="rounded bg-slate-100 text-slate-700 px-2.5 py-1 text-xs font-bold border border-slate-200">NOT FOUND</span>;
      default:
        return <span className="rounded bg-blue-100 text-blue-800 px-2.5 py-1 text-xs font-bold border border-blue-200">NEEDS REVIEW</span>;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Requirements & Evidence Review</h1>
          <p className="mt-1 text-sm text-slate-500">
            Verify automated evidence findings, inspect quoted passages, and record confirmed or overridden human determinations.
          </p>
        </div>

        {/* Filter Bar */}
        <div className="flex flex-wrap items-center gap-3">
          <select
            value={selectedContractId}
            onChange={(e) => setSelectedContractId(e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium focus:border-indigo-500 focus:outline-none bg-white shadow-sm"
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
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium focus:border-indigo-500 focus:outline-none bg-white shadow-sm"
          >
            {versions.map((v) => (
              <option key={v.id} value={v.id}>
                Version {v.version_number} ({v.approval_status})
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-xs text-red-800">
          {error}
        </div>
      )}

      {loading ? (
        <div className="py-20 text-center text-sm text-slate-500">Loading evidence findings…</div>
      ) : findings.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 bg-white p-12 text-center text-xs text-slate-500">
          No findings evaluated yet for this version. Navigate to the contract workspace and click &quot;Run Evaluation&quot;.
        </div>
      ) : (
        <div className="space-y-4">
          {findings.map((f) => (
            <div key={f.id} className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-bold text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded border border-indigo-100 uppercase tracking-wider">
                      {f.requirement_category || "General"}
                    </span>
                    <span className="text-slate-300">·</span>
                    <span className="text-xs text-slate-400">
                      Evaluated by {f.suggested_by}
                    </span>
                  </div>
                  <h3 className="text-base font-bold text-slate-900 mt-1">
                    {f.requirement_title}
                  </h3>
                </div>

                <div className="flex items-center gap-2.5">
                  <div className="flex flex-col items-end">
                    <span className="text-[10px] text-slate-400 uppercase font-semibold">Evaluation Status</span>
                    {getStatusBadge(f.status)}
                  </div>
                  {f.review_status !== "PROPOSED" && (
                    <div className="flex flex-col items-end">
                      <span className="text-[10px] text-slate-400 uppercase font-semibold">Review State</span>
                      <span className="rounded bg-purple-50 text-purple-700 px-2.5 py-1 text-xs font-bold border border-purple-200">
                        {f.review_status}
                      </span>
                    </div>
                  )}
                </div>
              </div>

              {/* Quoted Evidence Excerpt */}
              {f.evidence_quote ? (
                <div className="rounded-xl bg-slate-50/80 border border-slate-200 p-4 space-y-1.5">
                  <div className="flex items-center justify-between text-xs text-slate-500 font-semibold">
                    <span>Supporting Contractual Evidence Provenance:</span>
                    {f.evidence_page_number && (
                      <span className="text-indigo-600 bg-white px-2 py-0.5 rounded border border-slate-200">
                        Page {f.evidence_page_number} {f.evidence_section_title ? `· ${f.evidence_section_title}` : ""}
                      </span>
                    )}
                  </div>
                  <blockquote className="italic text-slate-900 font-serif border-l-4 border-indigo-600 pl-3 py-1 text-xs sm:text-sm">
                    &quot;{f.evidence_quote}&quot;
                  </blockquote>
                </div>
              ) : (
                <p className="text-xs text-slate-400 italic bg-slate-50 p-3 rounded-lg border border-slate-200">
                  No matching contractual passage located in this version.
                </p>
              )}

              {/* Analysis Notes */}
              {f.analysis_notes && (
                <div className="text-xs text-slate-700 bg-amber-50/60 border border-amber-200/70 p-3 rounded-xl space-y-1">
                  <span className="font-bold text-amber-950 uppercase tracking-wider text-[10px] block">
                    Automated Assessment Rationale:
                  </span>
                  <p className="leading-relaxed whitespace-pre-line">{f.analysis_notes}</p>
                </div>
              )}

              {/* Footer Decision Controls */}
              <div className="pt-3 border-t border-slate-100 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 text-xs">
                <div className="text-slate-400 text-[11px]">
                  Confidence: <strong className="text-slate-700">{f.confidence_score ? `${(f.confidence_score * 100).toFixed(0)}%` : "N/A"}</strong>
                  {f.reviewed_at && (
                    <span className="ml-3 text-slate-500">
                      Reviewed on {formatDate(f.reviewed_at)}
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleOpenDecisionModal(f, "CONFIRMED")}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-300 bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-800 hover:bg-emerald-100 transition shadow-sm"
                  >
                    <Check className="h-3.5 w-3.5" />
                    Confirm Suggestion
                  </button>
                  <button
                    onClick={() => handleOpenDecisionModal(f, "OVERRIDDEN")}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition shadow-sm"
                  >
                    <RotateCcw className="h-3.5 w-3.5" />
                    Override Determination
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Decision Modal */}
      {decisionModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl border border-slate-200">
            <h2 className="text-lg font-bold text-slate-900">
              {decisionType === "CONFIRMED" ? "Confirm Finding Outcome" : "Override Machine Determination"}
            </h2>
            <p className="text-xs text-slate-500 mt-1">
              Requirement: <strong>{activeFinding?.requirement_title}</strong>
            </p>

            <form onSubmit={handleSubmitDecision} className="mt-4 space-y-4 text-xs">
              {decisionType === "OVERRIDDEN" ? (
                <>
                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">New Human Overridden Status</label>
                    <select
                      value={overriddenStatus}
                      onChange={(e) => setOverriddenStatus(e.target.value)}
                      className="w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-indigo-500 focus:outline-none bg-white font-semibold"
                    >
                      <option value="SATISFIED">SATISFIED — Complies with policy</option>
                      <option value="NOT_SATISFIED">NOT_SATISFIED — Policy violation</option>
                      <option value="PARTIALLY_SATISFIED">PARTIALLY_SATISFIED — Incomplete</option>
                      <option value="NEEDS_REVIEW">NEEDS_REVIEW — Escalated to Legal</option>
                    </select>
                  </div>

                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">Override Reason / Justification</label>
                    <textarea
                      rows={3}
                      required
                      placeholder="Explain why the automated evaluation is being overridden..."
                      value={overrideReason}
                      onChange={(e) => setOverrideReason(e.target.value)}
                      className="w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-indigo-500 focus:outline-none"
                    />
                  </div>
                </>
              ) : (
                <div className="rounded-lg bg-emerald-50 p-3.5 border border-emerald-200 text-emerald-900 space-y-1">
                  <p className="font-semibold">Confirming Automated Result</p>
                  <p className="text-emerald-700">
                    You are certifying that the automated evaluation status (<strong>{activeFinding?.status}</strong>) is accurate based on the cited evidence.
                  </p>
                </div>
              )}

              <div className="rounded-lg bg-slate-50 p-3 border border-slate-200 text-slate-600">
                Acting Reviewer: <strong>{activeUser.name}</strong> ({activeUser.role}).
              </div>

              <div className="mt-6 flex justify-end gap-2.5">
                <button
                  type="button"
                  onClick={() => setDecisionModalOpen(false)}
                  className="rounded-lg border border-slate-300 px-3.5 py-2 font-semibold text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingDecision}
                  className="rounded-lg bg-indigo-600 px-4 py-2 font-semibold text-white shadow-sm hover:bg-indigo-700 disabled:opacity-50"
                >
                  {submittingDecision ? "Saving…" : "Save Review Decision"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
