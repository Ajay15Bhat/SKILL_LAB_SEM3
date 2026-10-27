"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  GitCompare,
  ArrowRight,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ShieldAlert,
  FileText,
  Layers,
  Sparkles,
  Diff,
} from "lucide-react";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/utils";

export default function ComparePage() {
  const searchParams = useSearchParams();

  const [contracts, setContracts] = useState<any[]>([]);
  const [selectedContractId, setSelectedContractId] = useState<string>("");
  const [versions, setVersions] = useState<any[]>([]);
  const [sourceVersionId, setSourceVersionId] = useState<string>("");
  const [targetVersionId, setTargetVersionId] = useState<string>("");

  const [diffResult, setDiffResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getContracts().then((cList) => {
      setContracts(cList);
      const queryContractId = searchParams.get("contract_id");
      if (queryContractId && cList.some((c) => c.id === queryContractId)) {
        setSelectedContractId(queryContractId);
      } else if (cList.length > 0) {
        setSelectedContractId(cList[0].id);
      }
    });
  }, [searchParams]);

  useEffect(() => {
    if (!selectedContractId) return;
    api.getContractVersions(selectedContractId).then((vList) => {
      setVersions(vList);
      if (vList.length >= 2) {
        // Default source = older version (v1), target = newer version (v2)
        const sorted = [...vList].sort((a, b) => a.version_number - b.version_number);
        setSourceVersionId(sorted[0].id);
        setTargetVersionId(sorted[sorted.length - 1].id);
      } else if (vList.length === 1) {
        setSourceVersionId(vList[0].id);
        setTargetVersionId(vList[0].id);
      }
    });
  }, [selectedContractId]);

  const handleRunDiff = async () => {
    if (!selectedContractId || !sourceVersionId || !targetVersionId) return;
    try {
      setLoading(true);
      setError(null);
      const res = await api.compareVersions(selectedContractId, sourceVersionId, targetVersionId);
      setDiffResult(res);
    } catch (err: any) {
      setError(err.message || "Failed to compare versions");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedContractId && sourceVersionId && targetVersionId) {
      handleRunDiff();
    }
  }, [sourceVersionId, targetVersionId]);

  const sourceVerObj = versions.find((v) => v.id === sourceVersionId);
  const targetVerObj = versions.find((v) => v.id === targetVersionId);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="rounded bg-purple-50 text-purple-700 px-2.5 py-0.5 text-xs font-bold border border-purple-200 uppercase tracking-wider flex items-center gap-1">
              <GitCompare className="h-3.5 w-3.5" /> Signature Feature
            </span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 mt-1">
            Contract Version Diff & Change Impact Engine
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Compare successive revisions, inspect word-level clause differences, and flag compliance requirements requiring fresh assessment.
          </p>
        </div>

        {/* Selectors */}
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

          <div className="flex items-center gap-1.5 bg-slate-100 p-1 rounded-lg border border-slate-200 text-xs font-medium">
            <select
              value={sourceVersionId}
              onChange={(e) => setSourceVersionId(e.target.value)}
              className="rounded bg-white px-2.5 py-1 border border-slate-200 focus:outline-none"
            >
              {versions.map((v) => (
                <option key={v.id} value={v.id}>
                  v{v.version_number} ({v.approval_status})
                </option>
              ))}
            </select>
            <ArrowRight className="h-3.5 w-3.5 text-slate-400" />
            <select
              value={targetVersionId}
              onChange={(e) => setTargetVersionId(e.target.value)}
              className="rounded bg-white px-2.5 py-1 border border-slate-200 focus:outline-none"
            >
              {versions.map((v) => (
                <option key={v.id} value={v.id}>
                  v{v.version_number} ({v.approval_status})
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={handleRunDiff}
            disabled={loading}
            className="rounded-lg bg-indigo-600 px-3.5 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-indigo-700 disabled:opacity-50"
          >
            {loading ? "Diffing…" : "Recompute Diff"}
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-xs text-red-800">
          {error}
        </div>
      )}

      {/* Version Status & Approval Comparison Banner (Guarantees Section 3 Acceptance Rule) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Source Version */}
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm space-y-1.5 text-xs">
          <div className="flex items-center justify-between">
            <span className="font-bold text-slate-800">
              Source Version {sourceVerObj?.version_number ?? 1}
            </span>
            <span
              className={`rounded-full px-2.5 py-0.5 text-[11px] font-bold ${
                sourceVerObj?.approval_status === "APPROVED"
                  ? "bg-emerald-100 text-emerald-800 border border-emerald-200"
                  : "bg-slate-100 text-slate-700 border border-slate-200"
              }`}
            >
              {sourceVerObj?.approval_status ?? "DRAFT"}
            </span>
          </div>
          <p className="text-slate-500 font-mono text-[11px]">
            SHA-256: {sourceVerObj?.sha256_checksum?.slice(0, 24)}…
          </p>
          <p className="text-slate-400 text-[11px]">
            Uploaded: {formatDate(sourceVerObj?.created_at)}
          </p>
        </div>

        {/* Target Version */}
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm space-y-1.5 text-xs">
          <div className="flex items-center justify-between">
            <span className="font-bold text-slate-800">
              Target Version {targetVerObj?.version_number ?? 2} (Revised)
            </span>
            <span
              className={`rounded-full px-2.5 py-0.5 text-[11px] font-bold ${
                targetVerObj?.approval_status === "APPROVED"
                  ? "bg-emerald-100 text-emerald-800 border border-emerald-200"
                  : "bg-amber-100 text-amber-800 border border-amber-200"
              }`}
            >
              {targetVerObj?.approval_status ?? "DRAFT"}
            </span>
          </div>
          <p className="text-slate-500 font-mono text-[11px]">
            SHA-256: {targetVerObj?.sha256_checksum?.slice(0, 24)}…
          </p>
          <div className="flex items-center justify-between pt-1">
            <span className="text-slate-400 text-[11px]">
              Uploaded: {formatDate(targetVerObj?.created_at)}
            </span>
            {targetVerObj?.approval_status !== "APPROVED" && (
              <span className="text-[10px] font-bold text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                Fresh Sign-off Required
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Change Impact & Flagged Requirements Alert Banner */}
      {diffResult?.diff_payload?.flagged_requirements?.length > 0 && (
        <div className="rounded-xl border border-amber-300 bg-amber-50/80 p-5 shadow-sm space-y-3">
          <div className="flex items-center gap-2.5 text-amber-900">
            <ShieldAlert className="h-5 w-5 text-amber-600" />
            <h3 className="text-sm font-bold">
              Change Impact Alert: {diffResult.diff_payload.flagged_requirements.length} Requirement(s) Flagged for Reassessment
            </h3>
          </div>
          <p className="text-xs text-amber-800">
            Modifications detected in clauses supporting these requirements. Previous approval on Version {sourceVerObj?.version_number} is historical; Version {targetVerObj?.version_number} requires re-evaluation before approval.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-1">
            {diffResult.diff_payload.flagged_requirements.map((req: any) => (
              <div key={req.requirement_id} className="rounded-lg bg-white p-3 border border-amber-200 text-xs shadow-xs">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">{req.category}</span>
                <p className="font-bold text-slate-900 mt-0.5">{req.title}</p>
                <div className="mt-1 flex items-center justify-between text-[11px] text-slate-500">
                  <span>Previous: <strong className="text-emerald-700">{req.previous_status}</strong></span>
                  <span className="text-amber-700 font-medium">{req.reason}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Clause-by-Clause Granular Differences */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <Diff className="h-4 w-4 text-indigo-600" />
            Clause-by-Clause Textual Differences
          </h2>
          <span className="text-xs text-slate-500">
            {diffResult?.diff_payload?.metrics?.modifications ?? 0} modified, {diffResult?.diff_payload?.metrics?.additions ?? 0} added, {diffResult?.diff_payload?.metrics?.deletions ?? 0} removed
          </span>
        </div>

        {loading ? (
          <div className="py-12 text-center text-sm text-slate-500">Computing granular diff…</div>
        ) : !diffResult?.diff_payload?.modified_clauses?.length &&
          !diffResult?.diff_payload?.added_clauses?.length &&
          !diffResult?.diff_payload?.removed_clauses?.length ? (
          <div className="rounded-xl border border-dashed border-slate-300 bg-white p-12 text-center text-xs text-slate-500">
            {diffResult?.diff_summary || "Select two distinct versions above to compare."}
          </div>
        ) : (
          <div className="space-y-4">
            {/* Modified Clauses */}
            {diffResult?.diff_payload?.modified_clauses?.map((clause: any, idx: number) => (
              <div key={idx} className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
                <div className="bg-slate-50 px-5 py-3 border-b border-slate-200 flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-slate-900">{clause.section_title || `Clause #${clause.clause_index}`}</span>
                    <span className="rounded bg-amber-100 text-amber-800 px-2 py-0.5 text-[10px] font-bold">
                      MODIFIED
                    </span>
                  </div>
                  <span className="text-slate-400">Page {clause.page_number}</span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-slate-200 text-xs">
                  {/* Left: Source v1 */}
                  <div className="p-5 space-y-2 bg-red-50/20">
                    <div className="text-[11px] font-bold text-red-700 uppercase tracking-wider">
                      Version {sourceVerObj?.version_number} (Original Passage)
                    </div>
                    <p className="font-serif leading-relaxed text-slate-800 whitespace-pre-wrap">
                      {clause.source_text}
                    </p>
                  </div>

                  {/* Right: Target v2 */}
                  <div className="p-5 space-y-2 bg-emerald-50/20">
                    <div className="text-[11px] font-bold text-emerald-700 uppercase tracking-wider">
                      Version {targetVerObj?.version_number} (Revised Passage)
                    </div>
                    <div className="font-serif leading-relaxed text-slate-800 whitespace-pre-wrap">
                      {clause.diff_tokens && clause.diff_tokens.length > 0 ? (
                        clause.diff_tokens.map((token: any, tIdx: number) => {
                          if (token.type === "insert") {
                            return (
                              <mark key={tIdx} className="bg-emerald-200 text-emerald-950 font-bold px-1 rounded">
                                {token.text}{" "}
                              </mark>
                            );
                          } else if (token.type === "delete") {
                            return (
                              <span key={tIdx} className="bg-red-200 text-red-950 line-through px-1 rounded mr-1">
                                {token.text}{" "}
                              </span>
                            );
                          } else {
                            return <span key={tIdx}>{token.text} </span>;
                          }
                        })
                      ) : (
                        clause.target_text
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}

            {/* Added Clauses */}
            {diffResult?.diff_payload?.added_clauses?.map((clause: any, idx: number) => (
              <div key={idx} className="rounded-xl border border-emerald-200 bg-emerald-50/30 p-4 shadow-sm text-xs space-y-2">
                <div className="flex items-center justify-between font-bold text-emerald-800">
                  <span>Clause #{clause.clause_index}: {clause.section_title || "Newly Added Clause"}</span>
                  <span className="rounded bg-emerald-100 text-emerald-800 px-2 py-0.5 text-[10px]">ADDED IN V{targetVerObj?.version_number}</span>
                </div>
                <p className="font-serif text-slate-800 leading-relaxed">{clause.target_text}</p>
              </div>
            ))}

            {/* Removed Clauses */}
            {diffResult?.diff_payload?.removed_clauses?.map((clause: any, idx: number) => (
              <div key={idx} className="rounded-xl border border-red-200 bg-red-50/30 p-4 shadow-sm text-xs space-y-2">
                <div className="flex items-center justify-between font-bold text-red-800">
                  <span>Clause #{clause.clause_index}: {clause.section_title || "Removed Clause"}</span>
                  <span className="rounded bg-red-100 text-red-800 px-2 py-0.5 text-[10px]">DELETED FROM V{sourceVerObj?.version_number}</span>
                </div>
                <p className="font-serif text-slate-600 line-through leading-relaxed">{clause.source_text}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
