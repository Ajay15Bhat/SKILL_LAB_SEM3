"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  FileText,
  AlertTriangle,
  CheckCircle2,
  Clock,
  GitCompare,
  UploadCloud,
  ArrowRight,
  ShieldAlert,
  Calendar,
  Layers,
  Activity,
  History,
} from "lucide-react";
import { api, getActiveUser } from "@/lib/api";
import { formatDate } from "@/lib/utils";

export default function OverviewPage() {
  const [metrics, setMetrics] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchMetrics = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getOverviewMetrics();
      setMetrics(data);
    } catch (err: any) {
      setError(err.message || "Failed to load overview metrics");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
    window.addEventListener("clausetrace_user_changed", fetchMetrics);
    return () => window.removeEventListener("clausetrace_user_changed", fetchMetrics);
  }, []);

  return (
    <div className="space-y-8">
      {/* Hero / Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-200 pb-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">
            Contract Intelligence & Governance
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Evidence-grounded change impact analysis, version-bound approvals, and obligation tracking.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link
            href="/upload"
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-xs font-semibold text-white shadow-sm hover:bg-indigo-700 transition"
          >
            <UploadCloud className="h-4 w-4" />
            Upload Contract Revision
          </Link>
          <Link
            href="/compare"
            className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-xs font-semibold text-slate-700 shadow-sm hover:bg-slate-50 transition"
          >
            <GitCompare className="h-4 w-4" />
            Compare Versions
          </Link>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800 flex items-center gap-3">
          <AlertTriangle className="h-5 w-5 text-red-600 shrink-0" />
          <div className="flex-1">
            <p className="font-semibold">Unable to connect to ClauseTrace backend</p>
            <p className="text-xs text-red-700">{error} (Verify backend is running at http://127.0.0.1:8000)</p>
          </div>
          <button
            onClick={fetchMetrics}
            className="rounded px-2.5 py-1 text-xs font-medium bg-red-100 hover:bg-red-200 text-red-900"
          >
            Retry
          </button>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Awaiting Review */}
        <div className="rounded-xl border border-amber-200 bg-gradient-to-br from-amber-50/50 to-white p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-amber-800 uppercase tracking-wider">
              Awaiting Review
            </span>
            <div className="h-8 w-8 rounded-lg bg-amber-100 flex items-center justify-center text-amber-700">
              <Clock className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-3xl font-extrabold text-slate-900">
              {loading ? "…" : metrics?.contracts_awaiting_review ?? 0}
            </span>
            <p className="text-xs text-slate-500 mt-1">Revisions in DRAFT or IN_REVIEW state</p>
          </div>
        </div>

        {/* Findings Needing Attention */}
        <div className="rounded-xl border border-red-200 bg-gradient-to-br from-red-50/50 to-white p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-red-800 uppercase tracking-wider">
              Compliance Flags
            </span>
            <div className="h-8 w-8 rounded-lg bg-red-100 flex items-center justify-center text-red-700">
              <ShieldAlert className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-3xl font-extrabold text-slate-900">
              {loading ? "…" : metrics?.findings_requiring_attention ?? 0}
            </span>
            <p className="text-xs text-slate-500 mt-1">Non-compliant or review-needed findings</p>
          </div>
        </div>

        {/* Approved Versions */}
        <div className="rounded-xl border border-emerald-200 bg-gradient-to-br from-emerald-50/50 to-white p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-emerald-800 uppercase tracking-wider">
              Approved Versions
            </span>
            <div className="h-8 w-8 rounded-lg bg-emerald-100 flex items-center justify-center text-emerald-700">
              <CheckCircle2 className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-3xl font-extrabold text-slate-900">
              {loading ? "…" : metrics?.approved_versions_count ?? 0}
            </span>
            <p className="text-xs text-slate-500 mt-1">Sealed with cryptographic signatures</p>
          </div>
        </div>

        {/* Upcoming & Overdue Obligations */}
        <div className="rounded-xl border border-indigo-200 bg-gradient-to-br from-indigo-50/50 to-white p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-indigo-800 uppercase tracking-wider">
              Obligations & SLA
            </span>
            <div className="h-8 w-8 rounded-lg bg-indigo-100 flex items-center justify-center text-indigo-700">
              <Calendar className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-slate-900">
              {loading ? "…" : metrics?.upcoming_obligations_count ?? 0}
            </span>
            {metrics?.overdue_obligations_count > 0 && (
              <span className="rounded bg-red-100 text-red-700 px-1.5 py-0.5 text-xs font-bold">
                {metrics.overdue_obligations_count} overdue
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500 mt-1">Pending contractual commitments</p>
        </div>
      </div>

      {/* Main Grid: Workspaces & Recent Audit Trail */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left 2 Cols: Quick Workflows */}
        <div className="lg:col-span-2 space-y-6">
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between border-b border-slate-100 pb-4 mb-4">
              <div>
                <h2 className="text-base font-bold text-slate-900">Essential Review Workflows</h2>
                <p className="text-xs text-slate-500">Core capabilities for contract change impact management</p>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Link
                href="/upload"
                className="group p-4 rounded-xl border border-slate-200 hover:border-indigo-400 hover:shadow-md transition bg-slate-50/50 hover:bg-white"
              >
                <div className="h-8 w-8 rounded-lg bg-indigo-100 text-indigo-700 flex items-center justify-center mb-3 group-hover:bg-indigo-600 group-hover:text-white transition">
                  <UploadCloud className="h-4 w-4" />
                </div>
                <h3 className="text-sm font-semibold text-slate-900 group-hover:text-indigo-600">
                  1. Upload & Version Control
                </h3>
                <p className="text-xs text-slate-500 mt-1">
                  Upload PDF or DOCX. Creates immutable versions with SHA-256 fingerprinting.
                </p>
              </Link>

              <Link
                href="/reviews"
                className="group p-4 rounded-xl border border-slate-200 hover:border-indigo-400 hover:shadow-md transition bg-slate-50/50 hover:bg-white"
              >
                <div className="h-8 w-8 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center mb-3 group-hover:bg-emerald-600 group-hover:text-white transition">
                  <CheckCircle2 className="h-4 w-4" />
                </div>
                <h3 className="text-sm font-semibold text-slate-900 group-hover:text-indigo-600">
                  2. Evidence-Grounded Review
                </h3>
                <p className="text-xs text-slate-500 mt-1">
                  Evaluate termination notice, payment terms, and liability. Inspect exact quoted evidence.
                </p>
              </Link>

              <Link
                href="/compare"
                className="group p-4 rounded-xl border border-slate-200 hover:border-indigo-400 hover:shadow-md transition bg-slate-50/50 hover:bg-white"
              >
                <div className="h-8 w-8 rounded-lg bg-purple-100 text-purple-700 flex items-center justify-center mb-3 group-hover:bg-purple-600 group-hover:text-white transition">
                  <GitCompare className="h-4 w-4" />
                </div>
                <h3 className="text-sm font-semibold text-slate-900 group-hover:text-indigo-600">
                  3. Version Change Impact (Diff)
                </h3>
                <p className="text-xs text-slate-500 mt-1">
                  Compare v1 vs v2. Flags requirements altered by contract edits (e.g., 30d → 60d notice).
                </p>
              </Link>

              <Link
                href="/obligations"
                className="group p-4 rounded-xl border border-slate-200 hover:border-indigo-400 hover:shadow-md transition bg-slate-50/50 hover:bg-white"
              >
                <div className="h-8 w-8 rounded-lg bg-blue-100 text-blue-700 flex items-center justify-center mb-3 group-hover:bg-blue-600 group-hover:text-white transition">
                  <Calendar className="h-4 w-4" />
                </div>
                <h3 className="text-sm font-semibold text-slate-900 group-hover:text-indigo-600">
                  4. Obligation & SLA Tracker
                </h3>
                <p className="text-xs text-slate-500 mt-1">
                  Track vendor commitments, SOC2 reporting, and notice deadlines with automated overdue logic.
                </p>
              </Link>
            </div>
          </div>

          {/* Quick Notice about Immutability Guarantee */}
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-start gap-3.5">
              <div className="h-8 w-8 rounded-full bg-slate-100 flex items-center justify-center text-slate-600 shrink-0">
                <ShieldAlert className="h-4 w-4 text-indigo-600" />
              </div>
              <div className="text-xs text-slate-600 space-y-1">
                <p className="font-bold text-slate-900">Governance & Immutability Guarantee</p>
                <p>
                  ClauseTrace guarantees that every approval is bound to a single version SHA-256 fingerprint.
                  Uploading Version 2 will <strong>never silently inherit approval</strong> from Version 1, and previous
                  approvals remain permanently preserved in the historical ledger.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Right Col: Recent Audit Trail */}
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm flex flex-col">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-4">
            <div className="flex items-center gap-2">
              <History className="h-4 w-4 text-indigo-600" />
              <h2 className="text-sm font-bold text-slate-900">Recent Audit Ledger</h2>
            </div>
            <Link
              href="/audit"
              className="text-xs font-semibold text-indigo-600 hover:text-indigo-700 flex items-center gap-1"
            >
              Full log <ArrowRight className="h-3 w-3" />
            </Link>
          </div>

          <div className="flex-1 space-y-3.5">
            {loading ? (
              <p className="text-xs text-slate-400 py-4 text-center">Loading audit events…</p>
            ) : !metrics?.recent_audit_events?.length ? (
              <p className="text-xs text-slate-400 py-4 text-center">No audit events recorded yet.</p>
            ) : (
              metrics.recent_audit_events.map((event: any) => (
                <div key={event.id} className="text-xs border-l-2 border-indigo-500 pl-3 py-0.5">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-slate-800">
                      {event.action.replace(/_/g, " ")}
                    </span>
                    <span className="text-[10px] text-slate-400">
                      {formatDate(event.created_at)}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-500 mt-0.5">
                    Actor: <span className="text-slate-700 font-medium">{event.actor_email || "System"}</span> · Target: {event.entity_type}
                  </p>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
