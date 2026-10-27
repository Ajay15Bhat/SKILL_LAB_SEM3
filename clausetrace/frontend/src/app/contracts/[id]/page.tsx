"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  FileText,
  CheckCircle2,
  AlertTriangle,
  Clock,
  XCircle,
  GitCompare,
  UploadCloud,
  ShieldCheck,
  Building,
  Calendar,
  Layers,
  Search,
  Lock,
  ArrowRight,
  Sparkles,
} from "lucide-react";
import { api, getActiveUser } from "@/lib/api";
import { formatDate } from "@/lib/utils";

export default function ContractWorkspacePage() {
  const { id } = useParams() as { id: string };
  const router = useRouter();

  const [contract, setContract] = useState<any>(null);
  const [selectedVersion, setSelectedVersion] = useState<any>(null);
  const [clauses, setClauses] = useState<any[]>([]);
  const [findings, setFindings] = useState<any[]>([]);
  const [approvals, setApprovals] = useState<any[]>([]);
  const [auditEvents, setAuditEvents] = useState<any[]>([]);

  const [activeTab, setActiveTab] = useState<"findings" | "clauses" | "approvals" | "audit">("findings");
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Approval Modal State
  const [approvalModalOpen, setApprovalModalOpen] = useState(false);
  const [approvalDecision, setApprovalDecision] = useState<"APPROVED" | "REJECTED">("APPROVED");
  const [approvalComments, setApprovalComments] = useState("");
  const [approving, setApproving] = useState(false);

  // Upload Revision State
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);

  const activeUser = getActiveUser();

  const loadContractData = async () => {
    try {
      setLoading(true);
      setError(null);
      const c = await api.getContract(id);
      setContract(c);

      if (c.versions && c.versions.length > 0) {
        // Default to latest version
        const latest = c.versions[0];
        setSelectedVersion(latest);
        await loadVersionData(latest.id);
      }

      // Load contract audit trail
      try {
        const events = await api.getContractAuditEvents(id);
        setAuditEvents(events);
      } catch {}
    } catch (err: any) {
      setError(err.message || "Failed to load contract workspace");
    } finally {
      setLoading(false);
    }
  };

  const loadVersionData = async (versionId: string) => {
    try {
      const [cList, fList, aList] = await Promise.all([
        api.getVersionClauses(versionId).catch(() => []),
        api.getFindings({ version_id: versionId }).catch(() => []),
        api.getVersionApprovals(versionId).catch(() => []),
      ]);
      setClauses(cList);
      setFindings(fList);
      setApprovals(aList);
    } catch (err: any) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadContractData();
    window.addEventListener("clausetrace_user_changed", loadContractData);
    return () => window.removeEventListener("clausetrace_user_changed", loadContractData);
  }, [id]);

  const handleSelectVersion = async (v: any) => {
    setSelectedVersion(v);
    await loadVersionData(v.id);
  };

  const handleRunAnalysis = async () => {
    if (!selectedVersion) return;
    try {
      setAnalyzing(true);
      await api.runAnalysis(selectedVersion.id);
      await loadVersionData(selectedVersion.id);
      setActiveTab("findings");
      alert("Evidence-grounded requirement evaluation complete!");
    } catch (err: any) {
      alert(`Evaluation failed: ${err.message}`);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleApprove = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedVersion) return;
    try {
      setApproving(true);
      await api.approveVersion(selectedVersion.id, approvalDecision, approvalComments);
      setApprovalModalOpen(false);
      setApprovalComments("");
      await loadContractData();
      alert(`Version ${selectedVersion.version_number} has been officially ${approvalDecision.toLowerCase()}!`);
    } catch (err: any) {
      alert(`Approval error: ${err.message}`);
    } finally {
      setApproving(false);
    }
  };

  const handleUploadRevision = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) return;
    try {
      setUploading(true);
      await api.uploadVersion(id, uploadFile);
      setUploadModalOpen(false);
      setUploadFile(null);
      await loadContractData();
      alert("New version uploaded successfully!");
    } catch (err: any) {
      alert(`Upload failed: ${err.message}`);
    } finally {
      setUploading(false);
    }
  };

  const getStatusBadge = (status: string) => {
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

  const getFindingStatusBadge = (status: string) => {
    switch (status) {
      case "SATISFIED":
        return <span className="rounded bg-emerald-100 text-emerald-800 px-2 py-0.5 text-[11px] font-bold">SATISFIED</span>;
      case "NOT_SATISFIED":
        return <span className="rounded bg-red-100 text-red-800 px-2 py-0.5 text-[11px] font-bold">NOT SATISFIED</span>;
      case "PARTIALLY_SATISFIED":
        return <span className="rounded bg-amber-100 text-amber-800 px-2 py-0.5 text-[11px] font-bold">PARTIAL</span>;
      case "NOT_FOUND":
        return <span className="rounded bg-slate-100 text-slate-700 px-2 py-0.5 text-[11px] font-bold">NOT FOUND</span>;
      default:
        return <span className="rounded bg-blue-100 text-blue-800 px-2 py-0.5 text-[11px] font-bold">NEEDS REVIEW</span>;
    }
  };

  if (loading) {
    return <div className="py-20 text-center text-sm text-slate-500">Loading contract workspace…</div>;
  }

  if (error || !contract) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-center text-red-800">
        <p className="font-semibold">{error || "Contract not found"}</p>
        <Link href="/contracts" className="mt-4 inline-block text-xs font-bold text-red-900 underline">
          ← Back to Contracts
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Workspace Header */}
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-100 pb-5">
          <div>
            <div className="flex items-center gap-2">
              <span className="rounded bg-indigo-50 text-indigo-700 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider border border-indigo-100">
                {contract.contract_type}
              </span>
              <span className="text-xs text-slate-400">ID: {contract.id.slice(0, 8)}…</span>
            </div>
            <h1 className="mt-1.5 text-2xl font-extrabold tracking-tight text-slate-900">
              {contract.title}
            </h1>
            <div className="mt-1 flex items-center gap-4 text-xs text-slate-500">
              <span className="flex items-center gap-1 font-medium text-slate-700">
                <Building className="h-3.5 w-3.5 text-slate-400" />
                {contract.vendor_name}
              </span>
              <span>Created {formatDate(contract.created_at)}</span>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            <button
              onClick={() => setUploadModalOpen(true)}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 shadow-sm"
            >
              <UploadCloud className="h-4 w-4" />
              Upload New Revision
            </button>

            {contract.versions && contract.versions.length >= 2 && (
              <Link
                href={`/compare?contract_id=${contract.id}&source=${contract.versions[1]?.id}&target=${contract.versions[0]?.id}`}
                className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 shadow-sm"
              >
                <GitCompare className="h-4 w-4" />
                Compare Revisions
              </Link>
            )}

            <button
              onClick={handleRunAnalysis}
              disabled={analyzing || !selectedVersion}
              className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3.5 py-2 text-xs font-semibold text-white shadow-sm hover:bg-indigo-700 disabled:opacity-50"
            >
              <Sparkles className="h-4 w-4" />
              {analyzing ? "Evaluating…" : "Run Evaluation"}
            </button>

            <button
              onClick={() => setApprovalModalOpen(true)}
              disabled={!selectedVersion}
              className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3.5 py-2 text-xs font-semibold text-white shadow-sm hover:bg-emerald-700 disabled:opacity-50"
            >
              <ShieldCheck className="h-4 w-4" />
              Sign-off & Approve
            </button>
          </div>
        </div>

        {/* Immutable Version Selector Tabs */}
        <div className="mt-5 flex items-center gap-2 overflow-x-auto pb-1">
          <span className="text-xs font-bold text-slate-400 uppercase tracking-wider mr-2">
            Revisions:
          </span>
          {contract.versions?.map((v: any) => {
            const isSelected = selectedVersion?.id === v.id;
            return (
              <button
                key={v.id}
                onClick={() => handleSelectVersion(v)}
                className={`flex items-center gap-2 rounded-xl px-3.5 py-2 text-xs font-medium border transition ${
                  isSelected
                    ? "border-indigo-600 bg-indigo-50/70 text-indigo-900 shadow-sm font-semibold"
                    : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50 hover:border-slate-300"
                }`}
              >
                <span>Version {v.version_number}</span>
                {getStatusBadge(v.approval_status)}
              </button>
            );
          })}
        </div>

        {/* Selected Version Metadata Bar */}
        {selectedVersion && (
          <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50/80 p-3.5 flex flex-wrap items-center justify-between gap-4 text-xs">
            <div className="flex flex-wrap items-center gap-4">
              <div>
                <span className="text-slate-400 font-medium">Active File: </span>
                <span className="font-semibold text-slate-800">{selectedVersion.file_name}</span>
              </div>
              <div className="font-mono text-[11px] text-slate-500 bg-white px-2 py-0.5 rounded border border-slate-200">
                SHA-256: {selectedVersion.sha256_checksum.slice(0, 16)}…
              </div>
              <div>
                <span className="text-slate-400 font-medium">Uploaded: </span>
                <span className="text-slate-700">{formatDate(selectedVersion.created_at)}</span>
              </div>
            </div>

            {selectedVersion.approval_status === "APPROVED" && (
              <div className="flex items-center gap-1.5 text-emerald-800 font-medium bg-emerald-50 px-2.5 py-1 rounded-lg border border-emerald-200">
                <ShieldCheck className="h-4 w-4 text-emerald-600" />
                <span>Officially Sealed on {formatDate(selectedVersion.approved_at)}</span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Workspace Tabs */}
      <div className="border-b border-slate-200 flex gap-4 text-xs font-semibold">
        <button
          onClick={() => setActiveTab("findings")}
          className={`pb-3 border-b-2 transition ${
            activeTab === "findings" ? "border-indigo-600 text-indigo-600" : "border-transparent text-slate-500 hover:text-slate-900"
          }`}
        >
          Compliance Findings ({findings.length})
        </button>
        <button
          onClick={() => setActiveTab("clauses")}
          className={`pb-3 border-b-2 transition ${
            activeTab === "clauses" ? "border-indigo-600 text-indigo-600" : "border-transparent text-slate-500 hover:text-slate-900"
          }`}
        >
          Extracted Clauses ({clauses.length})
        </button>
        <button
          onClick={() => setActiveTab("approvals")}
          className={`pb-3 border-b-2 transition ${
            activeTab === "approvals" ? "border-indigo-600 text-indigo-600" : "border-transparent text-slate-500 hover:text-slate-900"
          }`}
        >
          Formal Sign-offs ({approvals.length})
        </button>
        <button
          onClick={() => setActiveTab("audit")}
          className={`pb-3 border-b-2 transition ${
            activeTab === "audit" ? "border-indigo-600 text-indigo-600" : "border-transparent text-slate-500 hover:text-slate-900"
          }`}
        >
          Audit History ({auditEvents.length})
        </button>
      </div>

      {/* Tab 1: Findings */}
      {activeTab === "findings" && (
        <div className="space-y-4">
          {findings.length === 0 ? (
            <div className="rounded-xl border border-dashed border-slate-300 bg-white p-12 text-center">
              <CheckCircle2 className="mx-auto h-10 w-10 text-slate-400" />
              <h3 className="mt-2 text-sm font-semibold text-slate-900">No findings evaluated yet</h3>
              <p className="mt-1 text-xs text-slate-500">
                Click &quot;Run Evaluation&quot; to test organizational requirements against this version.
              </p>
              <button
                onClick={handleRunAnalysis}
                disabled={analyzing}
                className="mt-4 rounded-lg bg-indigo-600 px-3.5 py-2 text-xs font-semibold text-white shadow-sm hover:bg-indigo-700"
              >
                {analyzing ? "Evaluating…" : "Run Evaluation Now"}
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              {findings.map((finding) => (
                <div key={finding.id} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm space-y-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                          {finding.requirement_category || "General"}
                        </span>
                        <span className="text-slate-300">·</span>
                        <span className="text-xs text-slate-400">
                          {finding.suggested_by}
                        </span>
                      </div>
                      <h4 className="text-sm font-bold text-slate-900 mt-0.5">
                        {finding.requirement_title || "Policy Requirement"}
                      </h4>
                    </div>

                    <div className="flex items-center gap-2">
                      {getFindingStatusBadge(finding.status)}
                      {finding.review_status !== "PROPOSED" && (
                        <span className="rounded bg-purple-50 text-purple-700 px-2 py-0.5 text-[10px] font-bold border border-purple-200">
                          {finding.review_status}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Supporting Evidence Excerpt */}
                  {finding.evidence_quote ? (
                    <div className="rounded-lg bg-slate-50 border border-slate-200 p-3 text-xs">
                      <div className="flex items-center justify-between text-slate-500 mb-1 font-medium">
                        <span>Supporting Contractual Evidence</span>
                        {finding.evidence_page_number && (
                          <span className="text-indigo-600">Page {finding.evidence_page_number}</span>
                        )}
                      </div>
                      <p className="italic text-slate-800 font-serif border-l-2 border-indigo-500 pl-2.5 my-1">
                        &quot;{finding.evidence_quote}&quot;
                      </p>
                    </div>
                  ) : (
                    <p className="text-xs text-slate-400 italic">No direct quotation found matching criteria.</p>
                  )}

                  {/* Analysis Notes */}
                  {finding.analysis_notes && (
                    <p className="text-xs text-slate-600 bg-amber-50/50 border border-amber-100 p-2.5 rounded-lg">
                      <strong className="text-amber-900 font-medium">Evaluation Analysis: </strong>
                      {finding.analysis_notes}
                    </p>
                  )}

                  <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-400">
                    <span>Confidence Score: {finding.confidence_score ? `${(finding.confidence_score * 100).toFixed(0)}%` : "N/A"}</span>
                    <Link
                      href="/reviews"
                      className="font-semibold text-indigo-600 hover:text-indigo-800 flex items-center gap-1"
                    >
                      Reviewer Decision Controls <ArrowRight className="h-3 w-3" />
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Extracted Clauses */}
      {activeTab === "clauses" && (
        <div className="space-y-3">
          {clauses.length === 0 ? (
            <div className="rounded-xl border border-dashed border-slate-300 bg-white p-12 text-center text-xs text-slate-500">
              No clauses extracted for this version.
            </div>
          ) : (
            clauses.map((c) => (
              <div key={c.id} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm space-y-2 text-xs">
                <div className="flex items-center justify-between text-slate-400 border-b border-slate-100 pb-2">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-slate-700">Clause #{c.clause_index}</span>
                    {c.section_title && (
                      <span className="rounded bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-700">
                        {c.section_title}
                      </span>
                    )}
                  </div>
                  <span>Page {c.page_number}</span>
                </div>
                <p className="text-slate-800 leading-relaxed font-serif">{c.text_content}</p>
                <div className="text-[10px] text-slate-400 font-mono">
                  Offset: [{c.char_start} - {c.char_end}]
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Tab 3: Formal Approvals */}
      {activeTab === "approvals" && (
        <div className="space-y-3">
          {approvals.length === 0 ? (
            <div className="rounded-xl border border-dashed border-slate-300 bg-white p-12 text-center text-xs text-slate-500">
              No formal sign-offs recorded yet for this version.
            </div>
          ) : (
            approvals.map((a) => (
              <div key={a.id} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm space-y-3 text-xs">
                <div className="flex items-center justify-between">
                  <span
                    className={`font-bold px-2.5 py-1 rounded-full ${
                      a.decision === "APPROVED" ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-800"
                    }`}
                  >
                    {a.decision}
                  </span>
                  <span className="text-slate-400">{formatDate(a.created_at)}</span>
                </div>
                <div>
                  <p className="font-semibold text-slate-800">Approver: {a.approver_name || "Authorized Reviewer"}</p>
                  {a.comments && <p className="mt-1 text-slate-600 bg-slate-50 p-2.5 rounded border border-slate-200">{a.comments}</p>}
                </div>
                <div className="rounded bg-slate-50 p-2.5 border border-slate-200 font-mono text-[11px] text-slate-600 break-all">
                  <span className="font-bold text-slate-400 uppercase tracking-wider block mb-0.5">Cryptographic SHA-256 Seal:</span>
                  {a.signature_hash}
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Tab 4: Audit */}
      {activeTab === "audit" && (
        <div className="space-y-3">
          {auditEvents.length === 0 ? (
            <div className="rounded-xl border border-dashed border-slate-300 bg-white p-12 text-center text-xs text-slate-500">
              No audit logs recorded for this contract.
            </div>
          ) : (
            auditEvents.map((event) => (
              <div key={event.id} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm text-xs space-y-1">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-indigo-900">{event.action.replace(/_/g, " ")}</span>
                  <span className="text-slate-400">{formatDate(event.created_at)}</span>
                </div>
                <p className="text-slate-600">
                  Actor: <strong className="text-slate-800">{event.actor_email || "System"}</strong> · Target: {event.entity_type}
                </p>
                {event.metadata_after && (
                  <pre className="mt-2 rounded bg-slate-50 p-2 text-[11px] text-slate-600 font-mono overflow-x-auto">
                    {JSON.stringify(event.metadata_after, null, 2)}
                  </pre>
                )}
              </div>
            ))
          )}
        </div>
      )}

      {/* Modal: Formal Sign-off & Approval */}
      {approvalModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl border border-slate-200">
            <div className="flex items-center gap-2 text-indigo-600 mb-2">
              <ShieldCheck className="h-5 w-5" />
              <h2 className="text-lg font-bold text-slate-900">Official Version Sign-off</h2>
            </div>
            <p className="text-xs text-slate-500">
              Signs off on <strong>Version {selectedVersion?.version_number}</strong>. This approval is cryptographically
              bound to this revision and will not apply to future uploads.
            </p>

            <form onSubmit={handleApprove} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Decision</label>
                <select
                  value={approvalDecision}
                  onChange={(e: any) => setApprovalDecision(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-xs focus:border-indigo-500 focus:outline-none bg-white font-semibold"
                >
                  <option value="APPROVED">APPROVED — Meets Compliance</option>
                  <option value="REJECTED">REJECTED — Violations Identified</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Justification Comments</label>
                <textarea
                  rows={3}
                  required
                  placeholder="Record formal justification or legal conditions..."
                  value={approvalComments}
                  onChange={(e) => setApprovalComments(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-xs focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div className="rounded-lg bg-amber-50 p-3 border border-amber-200 text-[11px] text-amber-800">
                Current Role: <strong>{activeUser.role}</strong> ({activeUser.email}).
                {activeUser.role !== "REVIEWER" && activeUser.role !== "ADMIN" && (
                  <p className="text-red-600 font-semibold mt-1">
                    Warning: Only Reviewer or Admin roles are authorized to approve. Switch identity in top-right navbar to proceed.
                  </p>
                )}
              </div>

              <div className="mt-6 flex justify-end gap-2.5">
                <button
                  type="button"
                  onClick={() => setApprovalModalOpen(false)}
                  className="rounded-lg border border-slate-300 px-3.5 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={approving || (activeUser.role !== "REVIEWER" && activeUser.role !== "ADMIN")}
                  className="rounded-lg bg-emerald-600 px-4 py-2 text-xs font-semibold text-white shadow-sm hover:bg-emerald-700 disabled:opacity-50"
                >
                  {approving ? "Sealing…" : "Execute Sign-off"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Upload Revision */}
      {uploadModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl border border-slate-200">
            <h2 className="text-lg font-bold text-slate-900">Upload Successive Revision</h2>
            <p className="text-xs text-slate-500 mt-1">
              Upload a new version (e.g. Version {(contract.versions?.[0]?.version_number || 0) + 1}).
            </p>

            <form onSubmit={handleUploadRevision} className="mt-4 space-y-4">
              <div className="rounded-xl border-2 border-dashed border-slate-300 p-6 text-center hover:border-indigo-400">
                <input
                  type="file"
                  required
                  accept=".pdf,.docx,.txt"
                  onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                  className="text-xs"
                />
                <p className="text-[11px] text-slate-400 mt-2">Accepted formats: PDF, DOCX, TXT</p>
              </div>

              <div className="mt-6 flex justify-end gap-2.5">
                <button
                  type="button"
                  onClick={() => setUploadModalOpen(false)}
                  className="rounded-lg border border-slate-300 px-3.5 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={uploading || !uploadFile}
                  className="rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white shadow-sm hover:bg-indigo-700 disabled:opacity-50"
                >
                  {uploading ? "Uploading…" : "Upload Version"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
