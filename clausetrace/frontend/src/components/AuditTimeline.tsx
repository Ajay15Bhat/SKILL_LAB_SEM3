'use client';

import React from 'react';
import { AuditLog } from '@/lib/api';
import { History, RefreshCw } from 'lucide-react';

interface AuditTimelineProps {
  logs: AuditLog[];
  onRefresh: () => void;
  isLoading: boolean;
}

export const AuditTimeline: React.FC<AuditTimelineProps> = ({ logs, onRefresh, isLoading }) => {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
            <History className="w-4 h-4 text-bronze-400" />
            <span>Cryptographic Audit Ledger</span>
            <span className="text-xs text-forest-400 font-mono">(Append-Only via PostgreSQL Triggers)</span>
          </h2>
          <p className="text-xs text-forest-400">
            Chronological audit trail documenting all uploads, clause extractions, findings, overrides, diffs, and sign-offs.
          </p>
        </div>

        <button
          onClick={onRefresh}
          disabled={isLoading}
          className="text-xs text-bronze-300 hover:text-bronze-200 flex items-center gap-1.5 bg-forest-900/80 border border-bronze-500/30 px-3 py-1.5 rounded-lg transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          <span>Refresh Ledger</span>
        </button>
      </div>

      {logs.length === 0 ? (
        <div className="text-center py-12 text-forest-400 text-xs">
          No audit logs recorded yet.
        </div>
      ) : (
        <div className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-3 before:bottom-3 before:w-0.5 before:bg-forest-800">
          {logs.map((l) => {
            let badgeColor = 'bg-forest-900 text-slate-300 border-forest-700';
            if (l.action.includes('APPROVED')) badgeColor = 'bg-emerald-950 text-emerald-300 border-emerald-500/40';
            if (l.action.includes('OVERRIDDEN')) badgeColor = 'bg-amber-950 text-amber-300 border-amber-500/40';
            if (l.action.includes('DIFF')) badgeColor = 'bg-bronze-900/80 text-bronze-300 border-bronze-500/40';

            return (
              <div key={l.id} className="relative pl-6">
                <span className="absolute left-[-21px] top-1.5 w-3 h-3 rounded-full bg-bronze-400 border-2 border-forest-950" />
                <div className="glass-card rounded-xl p-3.5 border border-forest-800">
                  <div className="flex items-center justify-between gap-3 text-xs mb-1">
                    <span className={`font-bold font-mono px-2 py-0.5 rounded border text-[10px] ${badgeColor}`}>
                      {l.action}
                    </span>
                    <span className="text-forest-400 font-mono text-[11px]">
                      {new Date(l.created_at).toLocaleTimeString()} • {new Date(l.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  <div className="text-xs text-slate-200 mt-1">
                    <span className="text-forest-400">Actor:</span> <strong>{l.user_name}</strong> on{' '}
                    <span className="font-mono text-bronze-300">{l.entity_type}</span>
                  </div>
                  {l.details && Object.keys(l.details).length > 0 && (
                    <pre className="bg-forest-950/80 p-2 rounded text-[11px] font-mono text-slate-400 mt-2 overflow-x-auto border border-forest-900">
                      {JSON.stringify(l.details, null, 2)}
                    </pre>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

