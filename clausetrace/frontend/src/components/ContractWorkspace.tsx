'use client';

import React, { useState } from 'react';
import { Clause, Contract, ContractVersion } from '@/lib/api';
import { BookOpen, Search, Upload, Award, CheckCircle2, Sparkles } from 'lucide-react';

interface ContractWorkspaceProps {
  contract: Contract | null;
  activeVersion: ContractVersion | null;
  clauses: Clause[];
  onSelectVersion: (version: ContractVersion) => void;
  onUploadPDF: (file: File) => void;
  onApproveVersion: () => void;
  onReevaluate: () => void;
  isUploading: boolean;
}

export const ContractWorkspace: React.FC<ContractWorkspaceProps> = ({
  contract,
  activeVersion,
  clauses,
  onSelectVersion,
  onUploadPDF,
  onApproveVersion,
  onReevaluate,
  isUploading,
}) => {
  const [searchQuery, setSearchQuery] = useState('');

  const filteredClauses = clauses.filter((c) =>
    c.text_content.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (c.section_title && c.section_title.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  return (
    <div className="space-y-6">
      {/* Contract & Version Header Card */}
      <div className="glass-card rounded-2xl p-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <span className="text-xs px-2.5 py-1 rounded-md bg-forest-900/90 text-bronze-300 border border-bronze-500/30 font-mono">
                {contract?.contract_type || 'AGREEMENT'}
              </span>
              <h1 className="text-2xl font-bold text-slate-100">
                {contract?.title || 'No Contract Selected'}
              </h1>
            </div>
            <p className="text-xs text-forest-400 mt-1">
              {contract
                ? `Vendor: ${contract.vendor_name} • Created: ${new Date(contract.created_at).toLocaleDateString()}`
                : 'Select or create a contract from the top navigation'}
            </p>
          </div>

          {/* Upload Button */}
          {contract && (
            <div>
              <label className="bronze-btn cursor-pointer px-4 py-2 rounded-lg text-xs flex items-center gap-1.5 shadow">
                <Upload className="w-4 h-4" />
                <span>{isUploading ? 'Extracting & Indexing...' : 'Upload Revision (PDF)'}</span>
                <input
                  type="file"
                  accept=".pdf"
                  className="hidden"
                  disabled={isUploading}
                  onChange={(e) => {
                    if (e.target.files?.[0]) onUploadPDF(e.target.files[0]);
                  }}
                />
              </label>
            </div>
          )}
        </div>

        {/* Version Chips & Actions */}
        {contract && (
          <div className="mt-6 pt-5 border-t border-forest-800/60 flex items-center justify-between flex-wrap gap-4">
            <div className="flex items-center gap-2">
              {(contract.versions || []).map((v) => {
                const isSelected = activeVersion?.id === v.id;
                const isApproved = v.approval_status === 'APPROVED';
                return (
                  <button
                    key={v.id}
                    onClick={() => onSelectVersion(v)}
                    className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-mono transition ${
                      isSelected
                        ? 'bg-forest-800 text-bronze-200 border border-bronze-400/60 shadow-md'
                        : 'bg-forest-950 text-slate-400 border border-forest-800 hover:border-forest-700'
                    }`}
                  >
                    <span>v{v.version_number}</span>
                    <span
                      className={`text-[10px] px-1.5 py-0.5 rounded border ${
                        isApproved
                          ? 'bg-emerald-950/80 text-emerald-300 border-emerald-500/40'
                          : 'bg-amber-950/80 text-amber-300 border-amber-500/40'
                      }`}
                    >
                      {v.approval_status}
                    </span>
                  </button>
                );
              })}
            </div>

            {activeVersion && (
              <div className="flex items-center gap-2">
                <button
                  onClick={onReevaluate}
                  className="text-xs px-3 py-1.5 rounded-lg bg-forest-900/80 hover:bg-forest-850 text-slate-300 border border-forest-700/60 flex items-center gap-1.5 transition"
                >
                  <Sparkles className="w-3.5 h-3.5 text-bronze-400" />
                  <span>Re-evaluate AI</span>
                </button>

                {activeVersion.approval_status === 'APPROVED' ? (
                  <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-950/60 border border-emerald-500/40 text-emerald-300 text-xs font-mono">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Signed & Approved</span>
                  </div>
                ) : (
                  <button
                    onClick={onApproveVersion}
                    className="bronze-btn px-3.5 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 shadow"
                  >
                    <Award className="w-3.5 h-3.5" />
                    <span>Approve Version v{activeVersion.version_number}</span>
                  </button>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Clauses Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <BookOpen className="w-4 h-4 text-bronze-400" />
            <h2 className="text-sm font-semibold text-slate-200">
              Segmented Legal Clauses ({filteredClauses.length})
            </h2>
            <span className="text-xs text-forest-400 font-mono">Indexed via PostgreSQL tsvector</span>
          </div>

          <div className="relative">
            <Search className="w-4 h-4 text-forest-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search clauses..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-forest-950 border border-forest-800 text-xs text-slate-200 rounded-lg pl-9 pr-3 py-2 w-64 outline-none focus:border-bronze-400"
            />
          </div>
        </div>

        {filteredClauses.length === 0 ? (
          <div className="text-center py-12 text-forest-400 text-xs">
            {clauses.length === 0
              ? 'No clauses extracted yet. Select a contract or upload a PDF revision.'
              : 'No clauses matching search filter.'}
          </div>
        ) : (
          <div className="space-y-3">
            {filteredClauses.map((c) => (
              <div key={c.id} className="glass-card glass-card-hover rounded-xl p-4 transition">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-semibold text-bronze-300 bg-forest-950 px-2 py-0.5 rounded border border-bronze-500/20">
                      Clause {c.clause_index}
                    </span>
                    {c.section_title && (
                      <span className="text-xs font-semibold text-slate-200">{c.section_title}</span>
                    )}
                  </div>
                  <span className="text-[11px] text-forest-400 font-mono">Page {c.page_number}</span>
                </div>
                <p className="text-xs text-slate-300 leading-relaxed">{c.text_content}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

