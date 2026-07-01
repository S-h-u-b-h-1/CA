import React, { useState, useEffect } from "react";
import { api } from "../lib/api";
import { Link, RefreshCw, CheckCircle, AlertTriangle, Play, Loader2 } from "lucide-react";

interface AKKCIntegrationProps {
  onRefreshClients: () => void;
  onRefreshDocs: () => void;
}

export const AKKCIntegration: React.FC<AKKCIntegrationProps> = ({
  onRefreshClients,
  onRefreshDocs
}) => {
  const [status, setStatus] = useState<any | null>(null);
  
  // Connection Form
  const [url, setUrl] = useState("https://akkc-eight.vercel.app/api");
  const [apiKey, setApiKey] = useState("");
  
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState<string | null>(null); // CLIENTS, TASKS, BILLS
  const [syncResult, setSyncResult] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadStatus();
  }, []);

  const loadStatus = async () => {
    try {
      const data = await api.getAKKCStatus();
      setStatus(data);
      if (data.connected && data.base_url) {
        setUrl(data.base_url);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleConnect = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const data = await api.connectAKKC({ base_url: url, api_key: apiKey });
      setStatus(data);
      setApiKey("");
    } catch (err: any) {
      setError(err.message || "Failed to connect to AKKC");
    } finally {
      setLoading(false);
    }
  };

  const handleSync = async (entity: string) => {
    setSyncing(entity);
    setError(null);
    setSyncResult(null);
    try {
      const res = await api.syncAKKC(entity);
      setSyncResult({
        entity,
        count: res.synced_count,
        timestamp: new Date()
      });
      // Trigger global state updates
      if (entity === "CLIENTS") {
        onRefreshClients();
      }
      loadStatus();
    } catch (err: any) {
      setError(err.message || `Syncing ${entity.toLowerCase()} failed`);
    } finally {
      setSyncing(null);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">AKKC Practice Manager Integration</h1>
        <p className="text-sm text-slate-500 mt-1">Connect CA Intelligence with your deployed AKKC timesheet and productivity firm portal.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Connection Details */}
        <div className="bg-white border border-slate-200 rounded-lg p-5 card-shadow h-fit space-y-4">
          <h3 className="font-bold text-slate-900">Connection Settings</h3>

          {status && (
            <div className={`p-4 rounded border text-sm flex items-start space-x-3 ${
              status.connected 
                ? "bg-emerald-50/50 border-emerald-200 text-emerald-900" 
                : "bg-amber-50/50 border-amber-200 text-amber-900"
            }`}>
              {status.connected ? (
                <>
                  <CheckCircle className="h-5 w-5 text-emerald-600 shrink-0 mt-0.5" />
                  <div>
                    <p className="font-bold">Integration Active</p>
                    <p className="text-xs mt-1">Connected to: <span className="font-mono">{status.base_url}</span></p>
                    {status.last_synced_at && (
                      <p className="text-[10px] text-slate-500 mt-1">Last Synced: {new Date(status.last_synced_at).toLocaleString()}</p>
                    )}
                  </div>
                </>
              ) : (
                <>
                  <AlertTriangle className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
                  <div>
                    <p className="font-bold">Not Integrated</p>
                    <p className="text-xs mt-1">Provide your AKKC workspace API token to bridge clients, employees, and billing invoices.</p>
                  </div>
                </>
              )}
            </div>
          )}

          {error && (
            <div className="bg-red-50 p-3 rounded text-xs text-red-700">
              {error}
            </div>
          )}

          <form onSubmit={handleConnect} className="space-y-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700">AKKC URL Base</label>
              <input
                type="url"
                required
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-900 text-xs font-mono"
                placeholder="https://akkc-eight.vercel.app/api"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700">API Access Token</label>
              <input
                type="password"
                required={!status?.connected}
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-900 text-xs"
                placeholder="••••••••••••••••"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2 px-4 bg-slate-900 hover:bg-slate-800 text-white rounded-md text-sm font-semibold disabled:opacity-50 transition-colors"
            >
              {loading ? "Establishing..." : status?.connected ? "Update Credentials" : "Connect Platform"}
            </button>
          </form>
        </div>

        {/* Right Columns: Synchronization Control */}
        <div className="bg-white border border-slate-200 rounded-lg p-5 card-shadow lg:col-span-2 space-y-6">
          <div>
            <h3 className="font-bold text-slate-900">Sync Controls</h3>
            <p className="text-xs text-slate-500 mt-1">Manual synchronization hooks to query and cache AKKC workspace objects.</p>
          </div>

          {syncResult && (
            <div className="bg-emerald-50 text-emerald-800 p-4 rounded-md border border-emerald-100 text-xs flex justify-between items-center">
              <span>
                Successfully completed sync for **{syncResult.entity}**. Synced **{syncResult.count}** records!
              </span>
              <span className="text-slate-400 font-mono">
                {syncResult.timestamp.toLocaleTimeString()}
              </span>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Sync Clients */}
            <div className="border border-slate-200 p-4 rounded-md flex flex-col justify-between h-40">
              <div>
                <h4 className="font-bold text-slate-800 text-sm">Sync Client Profiles</h4>
                <p className="text-[11px] text-slate-500 mt-1 leading-relaxed">
                  Imports client names, PANs, GSTINs, and addresses. Caches items locally for AI scoping.
                </p>
              </div>
              <button
                onClick={() => handleSync("CLIENTS")}
                disabled={!status?.connected || syncing !== null}
                className="w-full py-2 px-3 bg-slate-100 hover:bg-slate-200 disabled:opacity-50 text-slate-800 rounded text-xs font-semibold flex items-center justify-center space-x-1.5 transition-colors"
              >
                {syncing === "CLIENTS" ? <Loader2 className="h-3 w-3 animate-spin" /> : <Play className="h-3 w-3" />}
                <span>{syncing === "CLIENTS" ? "Syncing..." : "Sync Clients"}</span>
              </button>
            </div>

            {/* Sync Tasks */}
            <div className="border border-slate-200 p-4 rounded-md flex flex-col justify-between h-40">
              <div>
                <h4 className="font-bold text-slate-800 text-sm">Sync Pending Tasks</h4>
                <p className="text-[11px] text-slate-500 mt-1 leading-relaxed">
                  Pulls firm task sheets, filings deadlines, and assignments. Bridges notices response files directly.
                </p>
              </div>
              <button
                onClick={() => handleSync("TASKS")}
                disabled={!status?.connected || syncing !== null}
                className="w-full py-2 px-3 bg-slate-100 hover:bg-slate-200 disabled:opacity-50 text-slate-800 rounded text-xs font-semibold flex items-center justify-center space-x-1.5 transition-colors"
              >
                {syncing === "TASKS" ? <Loader2 className="h-3 w-3 animate-spin" /> : <Play className="h-3 w-3" />}
                <span>{syncing === "TASKS" ? "Syncing..." : "Sync Tasks"}</span>
              </button>
            </div>

            {/* Sync Billing */}
            <div className="border border-slate-200 p-4 rounded-md flex flex-col justify-between h-40">
              <div>
                <h4 className="font-bold text-slate-800 text-sm">Sync Pending Billings</h4>
                <p className="text-[11px] text-slate-500 mt-1 leading-relaxed">
                  Bridges timesheet hours, billing milestones, and pending invoice totals for client billing summaries.
                </p>
              </div>
              <button
                onClick={() => handleSync("BILLS")}
                disabled={!status?.connected || syncing !== null}
                className="w-full py-2 px-3 bg-slate-100 hover:bg-slate-200 disabled:opacity-50 text-slate-800 rounded text-xs font-semibold flex items-center justify-center space-x-1.5 transition-colors"
              >
                {syncing === "BILLS" ? <Loader2 className="h-3 w-3 animate-spin" /> : <Play className="h-3 w-3" />}
                <span>{syncing === "BILLS" ? "Syncing..." : "Sync Billings"}</span>
              </button>
            </div>
          </div>

          <div className="bg-slate-50 border border-slate-200 p-4 rounded text-xs leading-relaxed text-slate-600">
            📌 **Note regarding data mapping:** CA Intelligence reads client master data scoping from AKKC APIs. Synced records can be deleted or updated in CA Intelligence independently without affecting the master AKKC client directory.
          </div>
        </div>
      </div>
    </div>
  );
};
