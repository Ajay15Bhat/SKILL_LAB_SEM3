"use client";

import { useEffect, useState } from "react";
import {
  History,
  Shield,
  Filter,
  CheckCircle2,
  Clock,
  User,
  ArrowRight,
  Lock,
} from "lucide-react";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/utils";

export default function AuditTimelinePage() {
  const [logs, setLogs] = useState<any[]>([]);
  const [actionFilter, setActionFilter] = useState<string>("ALL");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchLogs = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getAuditEvents();
      setLogs(data);
    } catch (err: any) {
      setError(err.message || "Failed to load audit history");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
    window.addEventListener("clausetrace_user_changed", fetchLogs);
    return () => window.removeEventListener("clausetrace_user_changed", fetchLogs);
  }, []);

  const filteredLogs = logs.filter((log) => {
    if (actionFilter === "ALL") return true;
    return log.action === actionFilter;
  });

  const getActionBadgeColor = (action: string) => {
    if (action.includes("APPROVAL_GRANTED")) return "bg-emerald-100 text-emerald-800 border-emerald-200";
    if (action.includes("APPROVAL_REJECTED")) return "bg-red-100 text-red-800 border-red-200";
    if (action.includes("DIFF_GENERATED")) return "bg-purple-100 text-purple-800 border-purple-200";
    if (action.includes("OVERRIDDEN")) return "bg-amber-100 text-amber-800 border-amber-200";
    if (action.includes("CONFIRMED")) return "bg-teal-100 text-teal-800 border-teal-200";
    return "bg-indigo-50 text-indigo-700 border-indigo-200";
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="rounded bg-slate-100 text-slate-700 px-2.5 py-0.5 text-xs font-bold border border-slate-200 uppercase tracking-wider flex items-center gap-1">
              <Lock className="h-3 w-3" /> Append-Only Ledger
            </span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 mt-1">
            Enterprise Audit Trail & Event Timeline
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Immutable log of all contract uploads, compliance analyses, reviewer overrides, and official sign-offs.
          </p>
        </div>

        {/* Filter */}
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-slate-400" />
          <select
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-semibold focus:border-indigo-500 focus:outline-none bg-white shadow-sm"
          >
            <option value="ALL">All Event Actions</option>
            <option value="DOCUMENT_UPLOADED">Document Uploaded</option>
            <option value="VERSION_CREATED">Version Created</option>
            <option value="REQUIREMENT_EVALUATED">Requirement Evaluated</option>
            <option value="DIFF_GENERATED">Diff Generated</option>
            <option value="APPROVAL_GRANTED">Approval Granted</option>
            <option value="APPROVAL_REJECTED">Approval Rejected</option>
            <option value="FINDING_CONFIRMED">Finding Confirmed</option>
            <option value="FINDING_OVERRIDDEN">Finding Overridden</option>
            <option value="OBLIGATION_CREATED">Obligation Created</option>
            <option value="OBLIGATION_STATUS_CHANGED">Obligation Status Changed</option>
          </select>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-xs text-red-800">
          {error}
        </div>
      )}

      {loading ? (
        <div className="py-20 text-center text-sm text-slate-500">Loading audit history…</div>
      ) : filteredLogs.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 bg-white p-12 text-center text-xs text-slate-500">
          No audit events recorded yet. Upload a contract version to begin recording provenance.
        </div>
      ) : (
        <div className="relative border-l-2 border-slate-200 ml-4 space-y-6 pb-6">
          {filteredLogs.map((log) => (
            <div key={log.id} className="relative pl-6">
              {/* Dot */}
              <div className="absolute -left-[9px] top-1.5 h-4 w-4 rounded-full bg-white border-2 border-indigo-600 shadow-sm" />

              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm space-y-2 text-xs">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1">
                  <div className="flex items-center gap-2">
                    <span
                      className={`rounded-full px-2.5 py-0.5 text-[10px] font-bold border uppercase tracking-wider ${getActionBadgeColor(
                        log.action
                      )}`}
                    >
                      {log.action.replace(/_/g, " ")}
                    </span>
                    <span className="font-semibold text-slate-800">
                      Target: {log.entity_type} ({log.entity_id?.slice(0, 8)}…)
                    </span>
                  </div>
                  <span className="text-[11px] text-slate-400 font-mono">
                    {formatDate(log.created_at)}
                  </span>
                </div>

                <div className="flex items-center gap-1.5 text-slate-500 pt-1">
                  <User className="h-3.5 w-3.5 text-slate-400" />
                  <span>
                    Actor: <strong className="text-slate-800 font-medium">{log.actor_email || "System Service"}</strong>
                  </span>
                </div>

                {/* Metadata Payload Preview */}
                {(log.metadata_after || log.metadata_before) && (
                  <div className="mt-2 rounded-lg bg-slate-50 p-3 border border-slate-100 font-mono text-[11px] text-slate-700 overflow-x-auto">
                    {log.metadata_after && (
                      <div>
                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-0.5">Event Metadata:</span>
                        <pre className="whitespace-pre-wrap">{JSON.stringify(log.metadata_after, null, 2)}</pre>
                      </div>
                    )}
                    {log.metadata_before && (
                      <div className="mt-2 pt-2 border-t border-slate-200 text-slate-500">
                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-0.5">Previous State:</span>
                        <pre className="whitespace-pre-wrap">{JSON.stringify(log.metadata_before, null, 2)}</pre>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
