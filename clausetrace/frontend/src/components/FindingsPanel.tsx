'use client';

import React from 'react';
import { Finding } from '@/lib/api';
import { CheckCircle2, AlertTriangle, XCircle, Info, ShieldCheck, Check, Flag } from 'lucide-react';

interface FindingsPanelProps {
  findings: Finding[];
  onOverride: (findingId: string, newStatus: string) => void;
}

export const FindingsPanel: React.FC<FindingsPanelProps> = ({ findings, onOverride }) => {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-bronze-400" />
            <span>Compliance Rules & Grounded Findings ({findings.length})</span>
          </h2>
          <p className="text-xs text-forest-400">
            Strict Guardrail: Zero Silent Inheritance. Evaluated via PostgreSQL tsvector cover density + Google Gemini Flash.
          </p>
        </div>
      </div>

      {findings.length === 0 ? (
        <div className="text-center py-12 text-forest-400 text-xs">
          No compliance findings recorded for this revision. Click &quot;Re-evaluate AI&quot; in the workspace.
        </div>
      ) : (
        <div className="space-y-4">
          {findings.map((f) => {
            const isSatisfied = f.status === 'SATISFIED';
            const isNeedsReview = f.status === 'NEEDS_REVIEW';

            let badge = (
              <span className="px-2 py-0.5 text-xs font-bold rounded bg-rose-950/80 text-rose-300 border border-rose-500/40 flex items-center gap-1">
                <XCircle className="w-3 h-3" />
                <span>{f.status}</span>
              </span>
            );

            if (isSatisfied) {
              badge = (
                <span className="px-2 py-0.5 text-xs font-bold rounded bg-emerald-950/80 text-emerald-300 border border-emerald-500/40 flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3" />
                  <span>SATISFIED</span>
                </span>
              );
            } else if (isNeedsReview) {
              badge = (
                <span className="px-2 py-0.5 text-xs font-bold rounded bg-amber-950/80 text-amber-300 border border-amber-500/40 animate-pulse flex items-center gap-1">
                  <AlertTriangle className="w-3 h-3" />
                  <span>NEEDS_REVIEW</span>
                </span>
              );
            }

            return (
              <div
                key={f.id}
                className={`glass-card rounded-xl p-5 border transition ${
                  isNeedsReview ? 'border-amber-500/50 bg-amber-950/10' : 'border-bronze-500/20'
                }`}
              >
                <div className="flex items-center justify-between gap-4 mb-3">
                  <div>
                    <span className="text-xs text-forest-400 font-mono uppercase">Rule Requirement</span>
                    <h3 className="text-sm font-bold text-slate-100">{f.requirement_title}</h3>
                  </div>
                  <div className="flex items-center gap-3">
                    {badge}
                    {f.confidence_score && (
                      <span className="text-xs font-mono text-bronze-400">
                        {Math.round(f.confidence_score * 100)}% match
                      </span>
                    )}
                  </div>
                </div>

                {/* Evidence Quote Box */}
                {f.evidence_quote && (
                  <div className="bg-forest-950/80 rounded-lg p-3 border-l-2 border-bronze-400 my-2.5">
                    <div className="text-[10px] uppercase font-mono text-bronze-400 mb-1">
                      Evidence Quote {f.clause_page ? `(Page ${f.clause_page})` : ''}
                    </div>
                    <p className="text-xs italic text-slate-200">&ldquo;{f.evidence_quote}&rdquo;</p>
                  </div>
                )}

                {/* Analysis Notes */}
                <div className="text-xs text-slate-300 mt-2 flex items-start gap-2">
                  <Info className="w-4 h-4 text-forest-400 shrink-0 mt-0.5" />
                  <span>{f.analysis_notes || 'Evaluated via Hybrid Retrieval Pipeline.'}</span>
                </div>

                {/* Reviewer Sign-Off / Override Control */}
                <div className="mt-3 pt-3 border-t border-forest-800/60 flex items-center justify-between text-xs">
                  <span className="text-[11px] text-forest-400">
                    Review Status: <strong className="text-slate-200">{f.review_status}</strong>
                  </span>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => onOverride(f.id, 'SATISFIED')}
                      className="px-2.5 py-1 rounded bg-forest-900 hover:bg-forest-850 text-emerald-300 border border-emerald-500/30 text-[11px] flex items-center gap-1 transition"
                    >
                      <Check className="w-3 h-3" />
                      <span>Confirm Satisfied</span>
                    </button>
                    <button
                      onClick={() => onOverride(f.id, 'NEEDS_REVIEW')}
                      className="px-2.5 py-1 rounded bg-forest-900 hover:bg-forest-850 text-amber-300 border border-amber-500/30 text-[11px] flex items-center gap-1 transition"
                    >
                      <Flag className="w-3 h-3" />
                      <span>Flag Review</span>
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

