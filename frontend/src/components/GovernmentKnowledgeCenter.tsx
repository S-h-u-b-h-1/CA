"use client";

import React, { useState, useEffect } from "react";
import { 
  ShieldCheck, RefreshCw, FileText, Pause, Play, AlertCircle, 
  Search, GitMerge, Settings, Clock, CheckCircle2, XCircle, ChevronRight, Info
} from "lucide-react";
import { api } from "../lib/api";

export default function GovernmentKnowledgeCenter() {
  const [activeTab, setActiveTab] = useState<"connectors" | "downloads" | "versions" | "schedules" | "logs">("connectors");
  const [connectors, setConnectors] = useState<any[]>([]);
  const [documents, setDocuments] = useState<any[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<any | null>(null);
  const [versionsData, setVersionsData] = useState<any>(null);
  const [syncLogs, setSyncLogs] = useState<any[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [selectedConnectorLogs, setSelectedConnectorLogs] = useState<any[]>([]);
  const [logConnectorName, setLogConnectorName] = useState<string | null>(null);

  useEffect(() => {
    loadConnectors();
    loadDocuments();
  }, []);

  const loadConnectors = async () => {
    try {
      setLoading(true);
      const data = await api.listConnectors();
      setConnectors(data);
    } catch (err) {
      console.error("Failed to load connectors:", err);
    } finally {
      setLoading(false);
    }
  };

  const loadDocuments = async () => {
    try {
      const data = await api.searchGovernmentDocuments(searchQuery, categoryFilter);
      setDocuments(data);
    } catch (err) {
      console.error("Failed to load government documents:", err);
    }
  };

  const handleManualSync = async (sourceId: string) => {
    try {
      await api.syncConnector(sourceId);
      alert("Manual sync request sent. Running connector in background.");
      setTimeout(loadConnectors, 2000);
    } catch (err: any) {
      alert(`Sync failed: ${err.message}`);
    }
  };

  const handlePause = async (sourceId: string) => {
    try {
      await api.pauseConnector(sourceId);
      loadConnectors();
    } catch (err: any) {
      alert(`Pause failed: ${err.message}`);
    }
  };

  const handleResume = async (sourceId: string) => {
    try {
      await api.resumeConnector(sourceId);
      loadConnectors();
    } catch (err: any) {
      alert(`Resume failed: ${err.message}`);
    }
  };

  const handleFetchLogs = async (sourceId: string, name: string) => {
    try {
      const data = await api.getConnectorLogs(sourceId);
      setSelectedConnectorLogs(data);
      setLogConnectorName(name);
      setActiveTab("logs");
    } catch (err: any) {
      alert(`Failed to fetch logs: ${err.message}`);
    }
  };

  const handleFetchVersions = async (doc: any) => {
    try {
      setSelectedDoc(doc);
      setVersionsData(null);
      const data = await api.getDocumentVersions(doc.id);
      setVersionsData(data);
      setActiveTab("versions");
    } catch (err: any) {
      alert(`Failed to load versions: ${err.message}`);
    }
  };

  return (
    <div className="space-y-6">
      {/* Upper Title Row */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Government Knowledge Acquisition</h1>
          <p className="text-sm text-slate-500 mt-1">
            Authoritative ingestion connectors, statutory indexing, paragraph diff versioning, and compliance registers.
          </p>
        </div>
        <button
          onClick={() => {
            loadConnectors();
            loadDocuments();
          }}
          disabled={loading}
          className="flex items-center gap-2 px-3 py-1.5 bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 font-semibold rounded-lg text-xs shadow-sm transition"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          Refresh Sources
        </button>
      </div>

      {/* Tabs */}
      <div className="border-b border-slate-200">
        <nav className="flex space-x-6 text-sm font-semibold">
          <button
            onClick={() => setActiveTab("connectors")}
            className={`pb-3 border-b-2 px-1 transition ${
              activeTab === "connectors"
                ? "border-blue-900 text-blue-900"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            Ingestion Connectors ({connectors.length})
          </button>
          <button
            onClick={() => {
              setActiveTab("downloads");
              loadDocuments();
            }}
            className={`pb-3 border-b-2 px-1 transition ${
              activeTab === "downloads"
                ? "border-blue-900 text-blue-900"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            Download Registry
          </button>
          <button
            onClick={() => setActiveTab("versions")}
            className={`pb-3 border-b-2 px-1 transition ${
              activeTab === "versions"
                ? "border-blue-900 text-blue-900"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            Revision Diffs
          </button>
          <button
            onClick={() => setActiveTab("schedules")}
            className={`pb-3 border-b-2 px-1 transition ${
              activeTab === "schedules"
                ? "border-blue-900 text-blue-900"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            Task Schedules
          </button>
          <button
            onClick={() => setActiveTab("logs")}
            className={`pb-3 border-b-2 px-1 transition ${
              activeTab === "logs"
                ? "border-blue-900 text-blue-900"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            Execution Logs
          </button>
        </nav>
      </div>

      {activeTab === "connectors" && (
        <div>
          {loading && connectors.length === 0 ? (
            <div className="text-center py-12 text-slate-400 text-sm">
              <RefreshCw className="h-6 w-6 animate-spin mx-auto mb-2 text-slate-400" />
              Initializing Connector Registry...
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {connectors.map((conn) => (
                <div
                  key={conn.id}
                  className="bg-white border border-slate-200 rounded-lg p-5 card-shadow flex flex-col justify-between"
                >
                  <div className="space-y-3">
                    <div className="flex justify-between items-start">
                      <div>
                        <h3 className="text-sm font-bold text-slate-900 tracking-tight">{conn.connector_name}</h3>
                        <span className="text-[10px] font-semibold text-slate-450 uppercase">{conn.authority}</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        {conn.health === "HEALTHY" ? (
                          <span className="px-1.5 py-0.5 bg-emerald-50 text-emerald-700 rounded text-[9px] font-bold border border-emerald-100 flex items-center gap-1">
                            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" /> Healthy
                          </span>
                        ) : conn.health === "DOWN" ? (
                          <span
                            className="px-1.5 py-0.5 bg-slate-100 text-slate-600 rounded text-[9px] font-bold border border-slate-200 flex items-center gap-1"
                            title="No real official source could be reached for this authority - not a transient blip."
                          >
                            <span className="h-1.5 w-1.5 rounded-full bg-slate-400" /> Unavailable
                          </span>
                        ) : (
                          <span className="px-1.5 py-0.5 bg-amber-50 text-amber-700 rounded text-[9px] font-bold border border-amber-100 flex items-center gap-1">
                            <span className="h-1.5 w-1.5 rounded-full bg-amber-500" /> Degraded
                          </span>
                        )}
                        {conn.status === "RUNNING" ? (
                          <span className="px-1.5 py-0.5 bg-blue-50 text-blue-700 rounded text-[9px] font-bold border border-blue-100">
                            Active
                          </span>
                        ) : (
                          <span className="px-1.5 py-0.5 bg-rose-50 text-rose-700 rounded text-[9px] font-bold border border-rose-100">
                            Paused
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Metrics Block */}
                    <div className="grid grid-cols-2 gap-3 my-4 bg-slate-50 p-3 rounded-lg border border-slate-150 text-xs">
                      <div>
                        <span className="text-[9px] text-slate-500 block uppercase font-bold">Total Ingested</span>
                        <span className="text-sm font-bold text-slate-900 mt-0.5 block">{conn.total_documents_count} docs</span>
                      </div>
                      <div>
                        <span className="text-[9px] text-slate-500 block uppercase font-bold">Rate Limits</span>
                        <span className="text-xs font-semibold text-slate-800 mt-0.5 block font-mono">{conn.rate_limits}</span>
                      </div>
                      <div>
                        <span className="text-[9px] text-slate-500 block uppercase font-bold">Latency</span>
                        <span className="text-xs font-semibold text-slate-800 mt-0.5 block font-mono">
                          {conn.average_response_time > 0 ? `${conn.average_response_time.toFixed(0)} ms` : "0 ms"}
                        </span>
                      </div>
                      <div>
                        <span className="text-[9px] text-slate-500 block uppercase font-bold">Revisions</span>
                        <span className="text-xs font-semibold text-slate-800 mt-0.5 block">{conn.version_count} versioned</span>
                      </div>
                    </div>

                    <div className="text-[11px] text-slate-600 space-y-1">
                      <div className="flex justify-between">
                        <span>Auth Requirements:</span>
                        <span className="font-mono text-slate-500">{conn.auth_requirements}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Last Success:</span>
                        <span className="text-slate-500">
                          {conn.last_success ? new Date(conn.last_success).toLocaleTimeString() : "Never"}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="mt-5 pt-3 border-t border-slate-100 flex gap-2">
                    <button
                      onClick={() => handleManualSync(conn.id)}
                      className="flex-grow py-1.5 bg-slate-900 hover:bg-slate-800 text-white rounded text-xs font-semibold tracking-tight transition inline-flex justify-center items-center gap-1"
                    >
                      <RefreshCw className="h-3 w-3" /> Sync Now
                    </button>
                    {conn.status === "RUNNING" ? (
                      <button
                        onClick={() => handlePause(conn.id)}
                        className="py-1.5 px-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-200 rounded text-xs font-semibold flex items-center justify-center gap-1 transition"
                        title="Pause Sync"
                      >
                        <Pause className="h-3 w-3" /> Pause
                      </button>
                    ) : (
                      <button
                        onClick={() => handleResume(conn.id)}
                        className="py-1.5 px-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-200 rounded text-xs font-semibold flex items-center justify-center gap-1 transition"
                        title="Resume Sync"
                      >
                        <Play className="h-3 w-3" /> Resume
                      </button>
                    )}
                    <button
                      onClick={() => handleFetchLogs(conn.id, conn.connector_name)}
                      className="px-2.5 py-1.5 bg-white hover:bg-slate-50 border border-slate-200 text-slate-600 rounded text-xs font-bold transition shadow-sm"
                    >
                      Logs
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === "downloads" && (
        <div className="bg-white border border-slate-200 rounded-lg p-5 card-shadow">
          <div className="flex gap-3 mb-6">
            <div className="relative flex-grow">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
              <input
                type="text"
                placeholder="Search circulars, notifications, document numbers or titles..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded-lg pl-10 pr-4 py-2 text-sm text-slate-800 placeholder-slate-450 focus:outline-none focus:border-blue-900 focus:bg-white transition"
              />
            </div>
            <button
              onClick={loadDocuments}
              className="px-4 py-2 bg-slate-900 text-white rounded-lg hover:bg-slate-800 text-sm font-semibold transition shadow-sm"
            >
              Search
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-150 text-slate-500 font-semibold">
                  <th className="py-2.5">Document Number</th>
                  <th className="py-2.5">Title</th>
                  <th className="py-2.5">Issuing Authority</th>
                  <th className="py-2.5">Issue Date</th>
                  <th className="py-2.5">Version</th>
                  <th className="py-2.5 text-right font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {documents.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-12 text-center text-slate-400">
                      No crawled documents found in the download registry.
                    </td>
                  </tr>
                ) : (
                  documents.map((doc) => (
                    <tr key={doc.id} className="hover:bg-slate-50/50">
                      <td className="py-3 font-mono font-bold text-blue-900">{doc.document_number}</td>
                      <td className="py-3 font-semibold text-slate-900">{doc.title}</td>
                      <td className="py-3 text-slate-650">{doc.issuing_authority}</td>
                      <td className="py-3 text-slate-600">{doc.issue_date ? new Date(doc.issue_date).toLocaleDateString() : "N/A"}</td>
                      <td className="py-3">
                        <span className="px-1.5 py-0.5 bg-indigo-50 text-indigo-700 rounded font-bold font-mono border border-indigo-100">
                          v{doc.version}
                        </span>
                      </td>
                      <td className="py-3 text-right">
                        <button
                          onClick={() => handleFetchVersions(doc)}
                          className="px-2.5 py-1 bg-white hover:bg-slate-50 text-slate-750 rounded text-[10px] font-semibold border border-slate-200 shadow-sm transition inline-flex items-center gap-1"
                        >
                          View Diff <ChevronRight className="h-3 w-3" />
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === "versions" && (
        <div className="bg-white border border-slate-200 rounded-lg p-5 card-shadow">
          {!selectedDoc ? (
            <div className="text-center py-12 text-slate-400 text-sm">
              <GitMerge className="h-8 w-8 text-slate-300 mx-auto mb-3" />
              Please select a document from the **Download Registry** tab to explore revision differences.
            </div>
          ) : !versionsData ? (
            <div className="text-center py-12 text-slate-450">
              <RefreshCw className="h-8 w-8 animate-spin mx-auto text-indigo-600 mb-3" />
              Comparing version structures...
            </div>
          ) : (
            <div className="space-y-6">
              {/* Doc details */}
              <div className="border-b border-slate-150 pb-4">
                <span className="text-[10px] uppercase font-bold tracking-wider text-indigo-600">Version Diff Explorer</span>
                <h2 className="text-lg font-bold text-slate-900 mt-1">{selectedDoc.title}</h2>
                <div className="flex gap-4 mt-2 text-xs text-slate-500 font-mono">
                  <span>Doc Number: {selectedDoc.document_number}</span>
                  <span>Category: {selectedDoc.issuing_authority}</span>
                  <span>Active Version: v{selectedDoc.version}</span>
                </div>
              </div>

              {/* Version History chain */}
              <div>
                <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-3">Ingested Revision Chain</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {versionsData.versions.map((ver: any) => (
                    <div key={ver.id} className="p-4 bg-slate-50 border border-slate-200 rounded-lg relative overflow-hidden">
                      <div className="flex justify-between items-start">
                        <span className="px-2 py-0.5 bg-indigo-50 text-indigo-700 rounded-full font-bold font-mono text-[10px] border border-indigo-100">
                          Version {ver.version_number}
                        </span>
                        <span className="text-[10px] text-slate-450">{new Date(ver.created_at).toLocaleDateString()}</span>
                      </div>
                      <div className="mt-3 text-[11px] text-slate-500 font-mono">
                        <span className="block truncate">SHA256: {ver.checksum.slice(0, 16)}...</span>
                      </div>
                      {ver.version_number > 1 && (
                        <div className="mt-3 pt-3 border-t border-slate-150 space-y-1 text-[11px]">
                          <span className="text-emerald-700 block font-bold">+ {ver.added_paragraphs?.length || 0} Paragraphs Added</span>
                          <span className="text-rose-700 block font-bold">- {ver.removed_paragraphs?.length || 0} Paragraphs Removed</span>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Selected Diff Box */}
              {versionsData.versions.length <= 1 ? (
                <div className="bg-slate-50 p-4 border border-slate-200 rounded-lg text-center text-xs text-slate-500 flex items-center justify-center gap-2">
                  <Info className="h-4 w-4 text-slate-400" /> This document only has 1 version. Overwrite modifications to see diff logs.
                </div>
              ) : (
                <div className="space-y-4">
                  <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider">Bitwise Paragraph Differences (v2 vs v1)</h3>
                  {versionsData.versions.filter((v: any) => v.version_number > 1).map((ver: any) => (
                    <div key={ver.id} className="space-y-4">
                      {/* Added Paras */}
                      {ver.added_paragraphs?.length > 0 && (
                        <div className="space-y-2">
                          <span className="text-xs font-bold text-emerald-700 bg-emerald-50 border border-emerald-100 px-2 py-0.5 rounded">Added Text Blocks</span>
                          <div className="space-y-2 bg-emerald-50/30 border border-emerald-100 p-3 rounded-lg">
                            {ver.added_paragraphs.map((p: string, idx: number) => (
                              <p key={idx} className="text-xs text-emerald-900 leading-relaxed font-sans">{p}</p>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Removed Paras */}
                      {ver.removed_paragraphs?.length > 0 && (
                        <div className="space-y-2">
                          <span className="text-xs font-bold text-rose-750 bg-rose-50 border border-rose-100 px-2 py-0.5 rounded">Removed/Modified Text Blocks</span>
                          <div className="space-y-2 bg-rose-50/30 border border-rose-100 p-3 rounded-lg">
                            {ver.removed_paragraphs.map((p: string, idx: number) => (
                              <p key={idx} className="text-xs text-rose-900 leading-relaxed font-sans line-through">{p}</p>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {activeTab === "schedules" && (
        <div className="bg-white border border-slate-200 rounded-lg p-5 card-shadow">
          <div className="flex justify-between items-center mb-4">
            <div>
              <h2 className="text-md font-bold text-slate-900">Ingestion Schedules</h2>
              <p className="text-xs text-slate-500 mt-0.5">Automation frequency controls for crawler endpoints</p>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-150 text-slate-500 font-semibold">
                  <th className="py-2.5">Connector</th>
                  <th className="py-2.5">Authority</th>
                  <th className="py-2.5">Category</th>
                  <th className="py-2.5">Frequency</th>
                  <th className="py-2.5">Status</th>
                  <th className="py-2.5 text-right font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {connectors.map((conn) => (
                  <tr key={conn.id} className="hover:bg-slate-50/50">
                    <td className="py-3 font-semibold text-slate-900">{conn.connector_name}</td>
                    <td className="py-3 text-slate-650">{conn.authority}</td>
                    <td className="py-3 text-slate-600">{conn.category}</td>
                    <td className="py-3">
                      <span className="px-2 py-0.5 bg-slate-100 border border-slate-200 text-slate-700 rounded font-mono text-[10px]">
                        {conn.sync_frequency || "DAILY"}
                      </span>
                    </td>
                    <td className="py-3">
                      {conn.status === "RUNNING" ? (
                        <span className="text-emerald-700 font-bold">Active</span>
                      ) : (
                        <span className="text-rose-750 font-bold">Paused</span>
                      )}
                    </td>
                    <td className="py-3 text-right">
                      {conn.status === "RUNNING" ? (
                        <button
                          onClick={() => handlePause(conn.id)}
                          className="px-2.5 py-1 bg-rose-50 hover:bg-rose-100 border border-rose-200 text-rose-700 rounded text-[10px] font-bold transition"
                        >
                          Pause Ingestion
                        </button>
                      ) : (
                        <button
                          onClick={() => handleResume(conn.id)}
                          className="px-2.5 py-1 bg-emerald-50 hover:bg-emerald-100 border border-emerald-250 text-emerald-700 rounded text-[10px] font-bold transition"
                        >
                          Resume Ingestion
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === "logs" && (
        <div className="bg-white border border-slate-200 rounded-lg p-5 card-shadow">
          <div className="flex justify-between items-center mb-4">
            <div>
              <h2 className="text-md font-bold text-slate-900">
                {logConnectorName ? `Logs for: ${logConnectorName}` : "Execution Logs"}
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">Audit log records of connector synchronizations</p>
            </div>
          </div>

          <div className="space-y-3 max-h-[500px] overflow-y-auto pr-2">
            {selectedConnectorLogs.length === 0 ? (
              <div className="text-center py-12 text-slate-400 text-sm">
                No sync logs recorded for this source. Run "Sync Now" to populate logs.
              </div>
            ) : (
              selectedConnectorLogs.map((log: any) => (
                <div 
                  key={log.id} 
                  className={`p-3 border rounded-lg flex items-start justify-between gap-4 ${
                    log.status === "SUCCESS"
                      ? "bg-emerald-50 border-emerald-100 text-emerald-800"
                      : "bg-rose-50 border-rose-100 text-rose-800"
                  }`}
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      {log.status === "SUCCESS" ? (
                        <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                      ) : (
                        <XCircle className="h-4 w-4 text-rose-600" />
                      )}
                      <span className="font-bold text-xs uppercase font-mono">{log.status}</span>
                      <span className="text-[10px] text-slate-450 font-mono">
                        {new Date(log.sync_time).toLocaleString()}
                      </span>
                    </div>
                    {log.error_message && (
                      <p className="text-xs text-rose-900 font-medium leading-relaxed font-mono">{log.error_message}</p>
                    )}
                    <div className="text-[10px] text-slate-500 flex gap-4">
                      <span>Downloaded: {log.documents_downloaded} items</span>
                      <span>Duration: {log.duration_ms} ms</span>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
