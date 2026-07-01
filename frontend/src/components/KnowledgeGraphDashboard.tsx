import React, { useState, useEffect } from "react";
import { 
  GitFork, GitMerge, FileText, Search, RefreshCw, 
  UserCheck, ShieldCheck, Check, AlertCircle, Plus 
} from "lucide-react";
import { api } from "../lib/api";
import { CitationCard } from "./CitationCard";

export const KnowledgeGraphDashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState<"citations" | "entities" | "graph">("citations");
  
  // States for Citations
  const [citations, setCitations] = useState<any[]>([]);
  const [citationSearch, setCitationSearch] = useState("");
  const [loadingCitations, setLoadingCitations] = useState(false);
  
  // States for Entities
  const [entities, setEntities] = useState<any[]>([]);
  const [loadingEntities, setLoadingEntities] = useState(false);
  const [mergePrimary, setMergePrimary] = useState("");
  const [mergeSecondary, setMergeSecondary] = useState("");
  const [mergeMessage, setMergeMessage] = useState("");
  const [mergeError, setMergeError] = useState("");

  // States for Graph
  const [nodes, setNodes] = useState<any[]>([]);
  const [edges, setEdges] = useState<any[]>([]);
  const [loadingGraph, setLoadingGraph] = useState(false);

  // Load Citations
  const loadCitations = async () => {
    setLoadingCitations(true);
    try {
      if (citationSearch.trim()) {
        const res = await api.request<any[]>(`/api/v1/citations/search?q=${encodeURIComponent(citationSearch)}`);
        setCitations(res);
      } else {
        const res = await api.listCitations();
        setCitations(res);
      }
    } catch (err) {
      console.error("Failed to load citations", err);
    } finally {
      setLoadingCitations(false);
    }
  };

  // Load Entities
  const loadEntities = async () => {
    setLoadingEntities(true);
    try {
      const res = await api.listGraphNodes();
      // Filter for resolved entity nodes (PAN, GSTIN, CLIENT, etc.)
      setEntities(res.filter(n => ["PAN", "GSTIN", "CIN", "DIN", "CLIENT"].includes(n.node_type)));
    } catch (err) {
      console.error("Failed to load entities", err);
    } finally {
      setLoadingEntities(false);
    }
  };

  // Load Graph Nodes and Edges
  const loadGraphData = async () => {
    setLoadingGraph(true);
    try {
      const nRes = await api.listGraphNodes();
      const eRes = await api.listGraphEdges();
      setNodes(nRes);
      setEdges(eRes);
    } catch (err) {
      console.error("Failed to load graph data", err);
    } finally {
      setLoadingGraph(false);
    }
  };

  useEffect(() => {
    if (activeTab === "citations") {
      loadCitations();
    } else if (activeTab === "entities") {
      loadEntities();
    } else if (activeTab === "graph") {
      loadGraphData();
    }
  }, [activeTab]);

  const handleMerge = async (e: React.FormEvent) => {
    e.preventDefault();
    setMergeMessage("");
    setMergeError("");

    if (!mergePrimary || !mergeSecondary) {
      setMergeError("Both primary and secondary entities must be selected.");
      return;
    }
    if (mergePrimary === mergeSecondary) {
      setMergeError("Cannot merge an entity into itself.");
      return;
    }

    try {
      await api.mergeEntities(mergePrimary, mergeSecondary);
      setMergeMessage("Entities merged successfully! Relationships and citations have been re-wired.");
      setMergePrimary("");
      setMergeSecondary("");
      loadEntities();
    } catch (err: any) {
      setMergeError(err.message || "Failed to merge entities.");
    }
  };

  return (
    <div className="space-y-6">
      {/* Title */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight flex items-center gap-2">
            <GitFork className="h-6 w-6 text-blue-900" />
            Knowledge Graph & Citations
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Deduplicate entities, view tax coordinate linkages, and verify source-backed legal citations.
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-200 bg-white p-1 rounded-lg shadow-sm max-w-md">
        <button
          onClick={() => setActiveTab("citations")}
          className={`flex-1 py-2 px-4 text-center rounded-md text-xs font-bold transition-all duration-150 ${
            activeTab === "citations"
              ? "bg-blue-950 text-white shadow-sm"
              : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
          }`}
        >
          Citation Library
        </button>
        <button
          onClick={() => setActiveTab("entities")}
          className={`flex-1 py-2 px-4 text-center rounded-md text-xs font-bold transition-all duration-150 ${
            activeTab === "entities"
              ? "bg-blue-950 text-white shadow-sm"
              : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
          }`}
        >
          Entity Resolution
        </button>
        <button
          onClick={() => setActiveTab("graph")}
          className={`flex-1 py-2 px-4 text-center rounded-md text-xs font-bold transition-all duration-150 ${
            activeTab === "graph"
              ? "bg-blue-950 text-white shadow-sm"
              : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
          }`}
        >
          Graph Visualizer
        </button>
      </div>

      {/* Tab Contents */}
      {activeTab === "citations" && (
        <div className="space-y-4">
          {/* Search Bar */}
          <div className="flex gap-2 max-w-lg bg-white p-2 rounded-lg border border-slate-200 shadow-sm">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
              <input
                type="text"
                placeholder="Search citations by section, act, or keyword..."
                value={citationSearch}
                onChange={(e) => setCitationSearch(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && loadCitations()}
                className="w-full pl-9 pr-4 py-2 border-0 focus:ring-0 text-sm placeholder-slate-400 text-slate-900"
              />
            </div>
            <button
              onClick={loadCitations}
              className="bg-blue-950 text-white hover:bg-blue-900 px-4 py-2 rounded-md text-xs font-bold flex items-center gap-1.5 transition-colors"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loadingCitations ? "animate-spin" : ""}`} />
              Search
            </button>
          </div>

          {/* Citations Grid */}
          {loadingCitations ? (
            <div className="flex justify-center items-center py-12">
              <RefreshCw className="h-8 w-8 text-blue-950 animate-spin" />
            </div>
          ) : citations.length === 0 ? (
            <div className="bg-white p-8 border border-slate-200 rounded-lg text-center text-slate-500 text-sm">
              No citations found. Upload documents to automatically extract citations.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {citations.map((c) => (
                <CitationCard key={c.id} citation={c} />
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === "entities" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Merge Form */}
          <div className="lg:col-span-1 bg-white p-6 border border-slate-200 rounded-lg shadow-sm space-y-4 h-fit">
            <h3 className="text-sm font-bold text-slate-950 flex items-center gap-2">
              <GitMerge className="h-5 w-5 text-blue-900" />
              Merge Duplicates
            </h3>
            <p className="text-xs text-slate-500 leading-relaxed">
              Combine two entities that refer to the same individual or firm (e.g. typing variations).
            </p>

            <form onSubmit={handleMerge} className="space-y-4 pt-2">
              {/* Primary entity */}
              <div>
                <label className="block text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-1">
                  Keep Primary Entity
                </label>
                <select
                  value={mergePrimary}
                  onChange={(e) => setMergePrimary(e.target.value)}
                  className="w-full text-xs border border-slate-200 rounded p-2 focus:ring-1 focus:ring-blue-900"
                >
                  <option value="">Select Entity...</option>
                  {entities.map(e => (
                    <option key={e.id} value={e.properties?.entity_id}>
                      [{e.node_type}] {e.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Secondary entity */}
              <div>
                <label className="block text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-1">
                  Merge Secondary (to be deactivated)
                </label>
                <select
                  value={mergeSecondary}
                  onChange={(e) => setMergeSecondary(e.target.value)}
                  className="w-full text-xs border border-slate-200 rounded p-2 focus:ring-1 focus:ring-blue-900"
                >
                  <option value="">Select Entity...</option>
                  {entities.map(e => (
                    <option key={e.id} value={e.properties?.entity_id}>
                      [{e.node_type}] {e.label}
                    </option>
                  ))}
                </select>
              </div>

              {mergeError && (
                <div className="bg-rose-50 text-rose-700 text-xs p-3 rounded border border-rose-200 flex items-start gap-1.5">
                  <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                  <span>{mergeError}</span>
                </div>
              )}

              {mergeMessage && (
                <div className="bg-emerald-50 text-emerald-700 text-xs p-3 rounded border border-emerald-200 flex items-start gap-1.5">
                  <Check className="h-4 w-4 shrink-0 mt-0.5" />
                  <span>{mergeMessage}</span>
                </div>
              )}

              <button
                type="submit"
                className="w-full bg-blue-950 hover:bg-blue-900 text-white font-bold py-2 rounded text-xs transition-colors"
              >
                Merge Entities
              </button>
            </form>
          </div>

          {/* Active Entities List */}
          <div className="lg:col-span-2 bg-white p-6 border border-slate-200 rounded-lg shadow-sm space-y-4">
            <div className="flex justify-between items-center">
              <h3 className="text-sm font-bold text-slate-950 flex items-center gap-1.5">
                <UserCheck className="h-5 w-5 text-slate-700" />
                Deduplicated Entity Registry
              </h3>
              <button onClick={loadEntities} className="text-slate-400 hover:text-slate-600">
                <RefreshCw className={`h-4 w-4 ${loadingEntities ? "animate-spin" : ""}`} />
              </button>
            </div>

            {loadingEntities ? (
              <div className="flex justify-center items-center py-12">
                <RefreshCw className="h-6 w-6 text-blue-950 animate-spin" />
              </div>
            ) : entities.length === 0 ? (
              <div className="text-center text-slate-400 py-8 text-xs">
                No deduplicated entities active.
              </div>
            ) : (
              <div className="divide-y divide-slate-100 max-h-96 overflow-y-auto pr-2">
                {entities.map((e) => (
                  <div key={e.id} className="py-3 flex justify-between items-center gap-4 text-xs">
                    <div>
                      <p className="font-bold text-slate-900">{e.label}</p>
                      <p className="text-[10px] text-slate-500">ID: {e.properties?.entity_id}</p>
                    </div>
                    <span className="bg-slate-100 border border-slate-200 px-2 py-0.5 rounded text-[10px] text-slate-600 font-bold uppercase">
                      {e.node_type}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === "graph" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Nodes List */}
          <div className="lg:col-span-1 bg-white p-6 border border-slate-200 rounded-lg shadow-sm space-y-4 max-h-[500px] overflow-y-auto">
            <h3 className="text-sm font-bold text-slate-950 flex items-center gap-1.5">
              Nodes ({nodes.length})
            </h3>
            {loadingGraph ? (
              <div className="flex justify-center items-center py-12">
                <RefreshCw className="h-6 w-6 text-blue-950 animate-spin" />
              </div>
            ) : (
              <div className="space-y-2">
                {nodes.map(n => (
                  <div key={n.id} className="p-3 bg-slate-50 border border-slate-200 rounded-md text-xs space-y-1">
                    <div className="flex justify-between items-center">
                      <span className="font-bold text-slate-900 truncate max-w-[140px]">{n.label}</span>
                      <span className="bg-blue-100 text-blue-800 text-[9px] font-extrabold uppercase px-1.5 py-0.5 rounded">
                        {n.node_type}
                      </span>
                    </div>
                    {n.properties && Object.keys(n.properties).length > 0 && (
                      <div className="text-[10px] text-slate-500 font-mono overflow-hidden text-ellipsis">
                        {JSON.stringify(n.properties)}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Connected Links / Edges list */}
          <div className="lg:col-span-2 bg-white p-6 border border-slate-200 rounded-lg shadow-sm space-y-4 max-h-[500px] overflow-y-auto">
            <h3 className="text-sm font-bold text-slate-950 flex items-center gap-1.5">
              Relationships / Edges ({edges.length})
            </h3>
            {loadingGraph ? (
              <div className="flex justify-center items-center py-12">
                <RefreshCw className="h-6 w-6 text-blue-950 animate-spin" />
              </div>
            ) : edges.length === 0 ? (
              <div className="text-center text-slate-400 py-12 text-xs">
                No connections mapped in the graph yet.
              </div>
            ) : (
              <div className="space-y-3">
                {edges.map(e => {
                  const srcNode = nodes.find(n => n.id === e.source_node_id);
                  const tgtNode = nodes.find(n => n.id === e.target_node_id);
                  return (
                    <div key={e.id} className="p-4 bg-slate-50 border border-slate-100 rounded-lg flex items-center justify-between gap-4 text-xs">
                      <div className="flex-1 min-w-0">
                        <span className="font-semibold text-slate-900 block truncate">{srcNode ? srcNode.label : "Source"}</span>
                        <span className="text-[9px] text-slate-500 uppercase">{srcNode ? srcNode.node_type : "Node"}</span>
                      </div>
                      
                      <div className="shrink-0 flex flex-col items-center">
                        <span className="text-[10px] bg-blue-950 text-white font-bold px-2 py-0.5 rounded-full border border-blue-900 shadow-sm">
                          {e.relationship}
                        </span>
                        <div className="w-12 h-0.5 bg-slate-300 mt-1 relative">
                          <div className="absolute right-0 top-[-2px] w-1.5 h-1.5 bg-slate-500 rounded-full" />
                        </div>
                      </div>

                      <div className="flex-1 min-w-0 text-right">
                        <span className="font-semibold text-slate-900 block truncate">{tgtNode ? tgtNode.label : "Target"}</span>
                        <span className="text-[9px] text-slate-500 uppercase">{tgtNode ? tgtNode.node_type : "Node"}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
