'use client';

import React, { useEffect, useState } from 'react';
import {
  Contract,
  ContractVersion,
  Clause,
  Finding,
  DiffResult,
  AuditLog,
  fetchContracts,
  createContract,
  uploadContractVersion,
  fetchVersionClauses,
  fetchVersionFindings,
  evaluateVersion,
  approveVersion,
  overrideFinding,
  fetchDiff,
  fetchAuditLogs,
  seedDemoData,
} from '@/lib/api';
import { ContractWorkspace } from '@/components/ContractWorkspace';
import { FindingsPanel } from '@/components/FindingsPanel';
import { DiffViewer } from '@/components/DiffViewer';
import { AuditTimeline } from '@/components/AuditTimeline';
import {
  Scale,
  ShieldCheck,
  Code2,
  PlusCircle,
  Sparkles,
  FileText,
  CheckCheck,
  GitCompare,
  ShieldAlert,
  BookOpen,
  CheckCircle2,
  History,
  X,
} from 'lucide-react';

export default function Dashboard() {
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [activeContract, setActiveContract] = useState<Contract | null>(null);
  const [activeVersion, setActiveVersion] = useState<ContractVersion | null>(null);
  const [clauses, setClauses] = useState<Clause[]>([]);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [diffResult, setDiffResult] = useState<DiffResult | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);

  const [activeTab, setActiveTab] = useState<'clauses' | 'findings' | 'diff' | 'audit'>('clauses');
  const [isUploading, setIsUploading] = useState(false);
  const [isDiffLoading, setIsDiffLoading] = useState(false);
  const [isAuditLoading, setIsAuditLoading] = useState(false);
  const [isSeeding, setIsSeeding] = useState(false);

  // Modals
  const [showNewContractModal, setShowNewContractModal] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newVendor, setNewVendor] = useState('');
  const [newType, setNewType] = useState('MSA');

  useEffect(() => {
    loadAllContracts();
    loadAuditTrail();
  }, []);

  async function loadAllContracts() {
    try {
      const data = await fetchContracts();
      setContracts(data);
      if (data.length > 0) {
        selectContract(data[0]);
      }
    } catch (e) {
      console.error('Error fetching contracts:', e);
    }
  }

  async function loadAuditTrail() {
    setIsAuditLoading(true);
    try {
      const logs = await fetchAuditLogs();
      setAuditLogs(logs);
    } catch (e) {
      console.error('Error fetching audit logs:', e);
    } finally {
      setIsAuditLoading(false);
    }
  }

  function selectContract(contract: Contract) {
    setActiveContract(contract);
    const versions = contract.versions || [];
    if (versions.length > 0) {
      selectVersion(versions[0]);
    } else {
      setActiveVersion(null);
      setClauses([]);
      setFindings([]);
    }
  }

  async function selectVersion(version: ContractVersion) {
    setActiveVersion(version);
    try {
      const [clausesData, findingsData] = await Promise.all([
        fetchVersionClauses(version.id),
        fetchVersionFindings(version.id),
      ]);
      setClauses(clausesData);
      setFindings(findingsData);
    } catch (e) {
      console.error('Error loading version data:', e);
    }
  }

  async function handleUploadPDF(file: File) {
    if (!activeContract) return;
    setIsUploading(true);
    try {
      const newVer = await uploadContractVersion(activeContract.id, file);
      alert(`Uploaded Version v${newVer.version_number}\nSHA-256: ${newVer.sha256_checksum}`);
      await loadAllContracts();
      await loadAuditTrail();
    } catch (e: any) {
      alert(`Upload Failed: ${e.message}`);
    } finally {
      setIsUploading(false);
    }
  }

  async function handleApprove() {
    if (!activeVersion) return;
    const comments = prompt(
      `Reviewer Sign-Off Comments for v${activeVersion.version_number}:`,
      'Legal review complete. Approved.'
    );
    if (!comments) return;

    try {
      const resp = await approveVersion(activeVersion.id, comments);
      alert(`Version Approved!\nDigital Seal: ${resp.signature_hash}`);
      await loadAllContracts();
      await loadAuditTrail();
    } catch (e: any) {
      alert(`Approval error: ${e.message}`);
    }
  }

  async function handleReevaluate() {
    if (!activeVersion) return;
    try {
      const updatedFindings = await evaluateVersion(activeVersion.id);
      setFindings(updatedFindings);
      alert('Re-evaluation complete! Findings updated.');
    } catch (e: any) {
      alert(`Evaluation error: ${e.message}`);
    }
  }

  async function handleOverride(findingId: string, newStatus: string) {
    const notes = prompt(`Reviewer notes for setting status to ${newStatus}:`, 'Confirmed by Reviewer');
    if (!notes) return;
    try {
      await overrideFinding(findingId, newStatus, notes);
      if (activeVersion) {
        const updated = await fetchVersionFindings(activeVersion.id);
        setFindings(updated);
      }
      await loadAuditTrail();
    } catch (e: any) {
      alert(`Override error: ${e.message}`);
    }
  }

  async function handleCompare(sourceId: string, targetId: string) {
    if (!activeContract) return;
    setIsDiffLoading(true);
    try {
      const diff = await fetchDiff(activeContract.id, sourceId, targetId);
      setDiffResult(diff);
    } catch (e: any) {
      alert(`Diff error: ${e.message}`);
    } finally {
      setIsDiffLoading(false);
    }
  }

  async function handleSeedDemo() {
    setIsSeeding(true);
    try {
      await seedDemoData();
      await loadAllContracts();
      await loadAuditTrail();
      alert('Sample Contract (Cloud Services MSA) with v1 and v2 seeded successfully!');
    } catch (e: any) {
      alert(`Seeding error: ${e.message}`);
    } finally {
      setIsSeeding(false);
    }
  }

  async function handleCreateContract() {
    if (!newTitle || !newVendor) return alert('Please enter title and vendor.');
    try {
      await createContract({
        title: newTitle,
        vendor_name: newVendor,
        contract_type: newType,
      });
      setShowNewContractModal(false);
      setNewTitle('');
      setNewVendor('');
      await loadAllContracts();
    } catch (e: any) {
      alert(`Error creating contract: ${e.message}`);
    }
  }

  const approvedCount = contracts.reduce((acc, c) => {
    return acc + (c.versions || []).filter((v) => v.approval_status === 'APPROVED').length;
  }, 0);

  return (
    <div className="min-h-screen flex flex-col font-sans">
      {/* Top Navigation */}
      <header className="border-b border-bronze-500/20 bg-forest-950/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-forest-700 to-forest-900 border border-bronze-400/40 flex items-center justify-center shadow-lg shadow-forest-950/50">
              <Scale className="w-5 h-5 text-bronze-300" />
            </div>
            <div>
              <span className="text-xl font-bold tracking-tight bronze-gradient-text">ClauseTrace</span>
              <span className="text-xs text-forest-400 ml-2 px-2 py-0.5 rounded-full border border-forest-600/30 bg-forest-900/60 font-mono">
                v1.0 Academic Evaluation
              </span>
            </div>
          </div>

          <div className="hidden md:flex items-center gap-3">
            <div className="flex items-center gap-2 px-3 py-1 rounded-md bg-forest-900/80 border border-forest-700/40 text-xs">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-forest-400">PostgreSQL FTS + Gemini Flash Active</span>
            </div>
            <div className="flex items-center gap-1.5 px-3 py-1 rounded-md bg-bronze-900/40 border border-bronze-500/30 text-bronze-300 text-xs font-medium">
              <ShieldCheck className="w-3.5 h-3.5 text-bronze-400" />
              <span>Persona: Reviewer & Analyst</span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleSeedDemo}
              disabled={isSeeding}
              className="text-xs text-bronze-200 bg-forest-900/80 hover:bg-forest-800 border border-bronze-500/40 px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition disabled:opacity-50"
            >
              <Sparkles className="w-4 h-4 text-bronze-400" />
              <span>{isSeeding ? 'Seeding Samples...' : 'Load Demo Sample'}</span>
            </button>
            <a
              href="http://localhost:8000/docs"
              target="_blank"
              rel="noreferrer"
              className="text-xs text-bronze-300 hover:text-bronze-200 flex items-center gap-1.5 px-3 py-1.5 rounded-md hover:bg-forest-900/60 border border-transparent hover:border-bronze-500/30 transition"
            >
              <Code2 className="w-4 h-4" />
              <span className="font-mono">Swagger API</span>
            </a>
            <button
              onClick={() => setShowNewContractModal(true)}
              className="bronze-btn px-4 py-1.5 rounded-lg text-xs flex items-center gap-1.5 shadow"
            >
              <PlusCircle className="w-4 h-4" />
              <span>New Contract</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Stats Row */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="glass-card rounded-xl p-4 flex items-center gap-4">
            <div className="w-11 h-11 rounded-lg bg-forest-900/90 border border-bronze-500/20 flex items-center justify-center text-bronze-400">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xs text-forest-400 font-medium uppercase tracking-wider">Contracts</div>
              <div className="text-xl font-bold text-slate-100">{contracts.length}</div>
            </div>
          </div>

          <div className="glass-card rounded-xl p-4 flex items-center gap-4">
            <div className="w-11 h-11 rounded-lg bg-forest-900/90 border border-bronze-500/20 flex items-center justify-center text-emerald-400">
              <CheckCheck className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xs text-forest-400 font-medium uppercase tracking-wider">Approved Revisions</div>
              <div className="text-xl font-bold text-slate-100">{approvedCount}</div>
            </div>
          </div>

          <div className="glass-card rounded-xl p-4 flex items-center gap-4">
            <div className="w-11 h-11 rounded-lg bg-forest-900/90 border border-bronze-500/20 flex items-center justify-center text-bronze-300">
              <GitCompare className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xs text-forest-400 font-medium uppercase tracking-wider">Diff Engine</div>
              <div className="text-xs font-semibold text-bronze-300 font-mono mt-0.5">difflib + Impact Flags</div>
            </div>
          </div>

          <div className="glass-card rounded-xl p-4 flex items-center gap-4">
            <div className="w-11 h-11 rounded-lg bg-forest-900/90 border border-bronze-500/20 flex items-center justify-center text-amber-400">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xs text-forest-400 font-medium uppercase tracking-wider">Guardrail Status</div>
              <div className="text-xs font-semibold text-emerald-300 font-mono mt-0.5">Zero Silent Inheritance</div>
            </div>
          </div>
        </div>

        {/* Contract Picker */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <span className="text-xs text-forest-400 uppercase font-mono">Current Contract:</span>
            <select
              value={activeContract?.id || ''}
              onChange={(e) => {
                const found = contracts.find((c) => c.id === e.target.value);
                if (found) selectContract(found);
              }}
              className="bg-forest-950 border border-bronze-500/30 text-xs text-slate-200 rounded-lg px-3 py-1.5 outline-none focus:border-bronze-400"
            >
              {contracts.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.title} ({c.vendor_name})
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex items-center gap-2 border-b border-forest-800/80 mb-6 pb-2 overflow-x-auto">
          <button
            onClick={() => setActiveTab('clauses')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition ${
              activeTab === 'clauses'
                ? 'text-bronze-300 border-b-2 border-bronze-400 bg-forest-900/40'
                : 'text-slate-400 hover:text-slate-200 border-b-2 border-transparent'
            }`}
          >
            <BookOpen className="w-4 h-4" />
            <span>Clauses & Evidence ({clauses.length})</span>
          </button>

          <button
            onClick={() => setActiveTab('findings')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition ${
              activeTab === 'findings'
                ? 'text-bronze-300 border-b-2 border-bronze-400 bg-forest-900/40'
                : 'text-slate-400 hover:text-slate-200 border-b-2 border-transparent'
            }`}
          >
            <CheckCircle2 className="w-4 h-4" />
            <span>Compliance Findings ({findings.length})</span>
          </button>

          <button
            onClick={() => setActiveTab('diff')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition ${
              activeTab === 'diff'
                ? 'text-bronze-300 border-b-2 border-bronze-400 bg-forest-900/40'
                : 'text-slate-400 hover:text-slate-200 border-b-2 border-transparent'
            }`}
          >
            <GitCompare className="w-4 h-4" />
            <span>Version Diff & Change Impact</span>
          </button>

          <button
            onClick={() => setActiveTab('audit')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition ${
              activeTab === 'audit'
                ? 'text-bronze-300 border-b-2 border-bronze-400 bg-forest-900/40'
                : 'text-slate-400 hover:text-slate-200 border-b-2 border-transparent'
            }`}
          >
            <History className="w-4 h-4" />
            <span>Audit Trail Timeline ({auditLogs.length})</span>
          </button>
        </div>

        {/* Tab Panes */}
        {activeTab === 'clauses' && (
          <ContractWorkspace
            contract={activeContract}
            activeVersion={activeVersion}
            clauses={clauses}
            onSelectVersion={selectVersion}
            onUploadPDF={handleUploadPDF}
            onApproveVersion={handleApprove}
            onReevaluate={handleReevaluate}
            isUploading={isUploading}
          />
        )}

        {activeTab === 'findings' && (
          <FindingsPanel findings={findings} onOverride={handleOverride} />
        )}

        {activeTab === 'diff' && (
          <DiffViewer
            contract={activeContract}
            diffResult={diffResult}
            onCompare={handleCompare}
            isLoading={isDiffLoading}
          />
        )}

        {activeTab === 'audit' && (
          <AuditTimeline
            logs={auditLogs}
            onRefresh={loadAuditTrail}
            isLoading={isAuditLoading}
          />
        )}
      </main>

      {/* Modal: New Contract */}
      {showNewContractModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="glass-card rounded-2xl w-full max-w-md p-6 shadow-2xl border border-bronze-500/30">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                <PlusCircle className="w-5 h-5 text-bronze-400" />
                <span>Create Contract Container</span>
              </h3>
              <button
                onClick={() => setShowNewContractModal(false)}
                className="text-slate-400 hover:text-slate-200"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3.5 text-xs">
              <div>
                <label className="block text-forest-400 mb-1">Contract Title</label>
                <input
                  type="text"
                  placeholder="e.g. Master Services Agreement"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  className="w-full bg-forest-950 border border-forest-800 text-slate-200 rounded-lg p-2.5 outline-none focus:border-bronze-400"
                />
              </div>
              <div>
                <label className="block text-forest-400 mb-1">Vendor Name</label>
                <input
                  type="text"
                  placeholder="e.g. Acme Cloud Corp"
                  value={newVendor}
                  onChange={(e) => setNewVendor(e.target.value)}
                  className="w-full bg-forest-950 border border-forest-800 text-slate-200 rounded-lg p-2.5 outline-none focus:border-bronze-400"
                />
              </div>
              <div>
                <label className="block text-forest-400 mb-1">Contract Type</label>
                <select
                  value={newType}
                  onChange={(e) => setNewType(e.target.value)}
                  className="w-full bg-forest-950 border border-forest-800 text-slate-200 rounded-lg p-2.5 outline-none focus:border-bronze-400"
                >
                  <option value="MSA">Master Services Agreement (MSA)</option>
                  <option value="NDA">Non-Disclosure Agreement (NDA)</option>
                  <option value="SLA">Service Level Agreement (SLA)</option>
                  <option value="DPA">Data Processing Agreement (DPA)</option>
                </select>
              </div>
            </div>

            <div className="mt-6 flex items-center justify-end gap-2">
              <button
                onClick={() => setShowNewContractModal(false)}
                className="text-xs px-3.5 py-2 rounded-lg bg-forest-900 text-slate-300 border border-forest-800"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateContract}
                className="bronze-btn text-xs px-4 py-2 rounded-lg font-semibold"
              >
                Create Contract
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

