'use client';

import React, { useState } from 'react';
import { Contract, DiffResult } from '@/lib/api';
import { GitCompare, AlertTriangle } from 'lucide-react';

interface DiffViewerProps {
  contract: Contract | null;
  diffResult: DiffResult | null;
  onCompare: (sourceId: string, targetId: string) => void;
  isLoading: boolean;
}

export const DiffViewer: React.FC<DiffViewerProps> = ({
  contract,
  diffResult,
  onCompare,
  isLoading,
}) => {
  const versions = contract?.versions || [];
  const [sourceId, setSourceId] = useState<string>(
    versions.length >= 2 ? versions[versions.length - 1].id : (versions[0]?.id || '')
  );
  const [targetId, setTargetId] = useState<string>(
    versions[0]?.id || ''
  );

  return (
    <div className="space-y-6">
      {/* Comparator Controls Card */}
      <div className="glass-card rounded-xl p-5">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h2 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
              <GitCompare className="w-4 h-4 text-bronze-400" />
              <span>Contract Revisions Diff Comparator</span>
            </h2>
            <p className="text-xs text-forest-400 mt-0.5">
              Deterministic clause diffing with automated change-impact propagation
            </p>
          </div>

          <div className="flex items-center gap-2">
            <select
              value={sourceId}
              onChange={(e) => setSourceId(e.target.value)}
              className="bg-forest-950 border border-forest-800 text-xs text-slate-200 rounded-lg px-3 py-1.5 outline-none"
            >
              <option value="">Base Version...</option>
              {versions.map((v) => (
                <option key={v.id} value={v.id}>
                  v{v.version_number} ({v.approval_status})
                </option>
              ))}
            </select>
            <span className="text-xs text-forest-400">compare with</span>
            <select
              value={targetId}
              onChange={(e) => setTargetId(e.target.value)}
              className="bg-forest-950 border border-forest-800 text-xs text-slate-200 rounded-lg px-3 py-1.5 outline-none"
            >
              <option value="">Target Version...</option>
              {versions.map((v) => (
                <option key={v.id} value={v.id}>
                  v{v.version_number} ({v.approval_status})
                </option>
              ))}
            </select>
            <button
              onClick={() => {
                if (sourceId && targetId) onCompare(sourceId, targetId);
              }}
              disabled={isLoading || !sourceId || !targetId}
              className="bronze-btn px-4 py-1.5 rounded-lg text-xs font-semibold shadow disabled:opacity-50"
            >
              {isLoading ? 'Computing...' : 'Compare Revisions'}
            </button>
          </div>
        </div>

        {/* Diff Metrics Bar */}
        {diffResult && (
          <div className="mt-4 pt-4 border-t border-forest-800/80 grid grid-cols-4 gap-3 text-center">
            <div className="bg-forest-950/70 p-2.5 rounded-lg border border-forest-800">
              <div className="text-[10px] uppercase text-forest-400 font-mono">Additions</div>
              <div className="text-lg font-bold text-emerald-400">{diffResult.metrics.additions}</div>
            </div>
            <div className="bg-forest-950/70 p-2.5 rounded-lg border border-forest-800">
              <div className="text-[10px] uppercase text-forest-400 font-mono">Deletions</div>
              <div className="text-lg font-bold text-rose-400">{diffResult.metrics.deletions}</div>
            </div>
            <div className="bg-forest-950/70 p-2.5 rounded-lg border border-forest-800">
              <div className="text-[10px] uppercase text-forest-400 font-mono">Modified Clauses</div>
              <div className="text-lg font-bold text-amber-400">{diffResult.metrics.modifications}</div>
            </div>
            <div className="bg-forest-950/70 p-2.5 rounded-lg border border-forest-800">
              <div className="text-[10px] uppercase text-forest-400 font-mono">Unchanged</div>
              <div className="text-lg font-bold text-slate-300">{diffResult.metrics.unchanged}</div>
            </div>
          </div>
        )}
      </div>

      {/* Change Impact Warning Banner */}
      {diffResult && diffResult.impacted_requirements.length > 0 && (
        <div className="bg-amber-950/30 border border-amber-500/40 rounded-xl p-4">
          <div className="flex items-start gap-3">
            <div className="p-1.5 rounded-lg bg-amber-900/60 text-amber-300 mt-0.5">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <div className="flex-1">
              <h3 className="text-xs font-bold text-amber-200 uppercase tracking-wider">
                Change Impact Alert: Compliance Requirements Compromised
              </h3>
              <p className="text-xs text-amber-300/80 mt-0.5">
                The following compliance rules relied on clauses altered in this revision and are flagged for immediate re-verification:
              </p>
              <div className="mt-3 space-y-2">
                {diffResult.impacted_requirements.map((imp) => (
                  <div
                    key={imp.id}
                    className="bg-amber-950/60 p-3 rounded-lg border border-amber-500/30 text-xs"
                  >
                    <div className="font-bold text-amber-200">
                      Rule: {imp.title} ({imp.category})
                    </div>
                    <div className="text-amber-300/90 mt-0.5">{imp.impact_reason}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Clause-by-Clause Differences */}
      {diffResult ? (
        <div className="space-y-4">
          {diffResult.clause_diffs.map((c) => {
            let badge = (
              <span className="px-2 py-0.5 rounded text-[10px] font-mono text-slate-400 bg-forest-950">
                UNCHANGED
              </span>
            );
            let cardBorder = 'border-forest-800';

            if (c.change_type === 'MODIFIED') {
              badge = (
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-950 text-amber-300 border border-amber-500/40">
                  MODIFIED
                </span>
              );
              cardBorder = 'border-amber-500/40 bg-amber-950/10';
            } else if (c.change_type === 'ADDED') {
              badge = (
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950 text-emerald-300 border border-emerald-500/40">
                  ADDED
                </span>
              );
              cardBorder = 'border-emerald-500/40 bg-emerald-950/10';
            } else if (c.change_type === 'REMOVED') {
              badge = (
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-950 text-rose-300 border border-rose-500/40">
                  REMOVED
                </span>
              );
              cardBorder = 'border-rose-500/40 bg-rose-950/10';
            }

            return (
              <div key={c.clause_index} className={`glass-card rounded-xl p-4 border ${cardBorder}`}>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-bold text-bronze-300">
                      Clause {c.clause_index}
                    </span>
                    {c.section_title && (
                      <span className="text-xs font-semibold text-slate-200">{c.section_title}</span>
                    )}
                  </div>
                  {badge}
                </div>

                {c.change_type === 'MODIFIED' ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs mt-3">
                    <div className="bg-rose-950/20 p-3 rounded-lg border border-rose-900/40">
                      <div className="text-[10px] uppercase font-mono text-rose-400 mb-1">
                        v{diffResult.source_version_number} Base Text
                      </div>
                      <p className="text-rose-200/90 leading-relaxed">{c.source_text}</p>
                    </div>
                    <div className="bg-emerald-950/20 p-3 rounded-lg border border-emerald-900/40">
                      <div className="text-[10px] uppercase font-mono text-emerald-400 mb-1">
                        v{diffResult.target_version_number} Revised Text
                      </div>
                      <p className="text-emerald-200/90 leading-relaxed">{c.target_text}</p>
                    </div>
                  </div>
                ) : (
                  <p className="text-xs text-slate-300 leading-relaxed">
                    {c.target_text || c.source_text}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        <div className="text-center py-12 text-forest-400 text-xs">
          Select two versions above and click &quot;Compare Revisions&quot; to inspect changes.
        </div>
      )}
    </div>
  );
};

