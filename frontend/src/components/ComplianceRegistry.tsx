import React, { useState } from "react";
import { api } from "../lib/api";
import { Database, Globe, RefreshCw, Plus, ShieldCheck, ShieldAlert, Check } from "lucide-react";

interface ComplianceRegistryProps {
  sources: any[];
  currentUser: any;
  onRefresh: () => void;
}

export const ComplianceRegistry: React.FC<ComplianceRegistryProps> = ({
  sources,
  currentUser,
  onRefresh
}) => {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [sourceName, setSourceName] = useState("");
  const [category, setCategory] = useState("Income Tax");
  const [url, setUrl] = useState("");
  const [accessType, setAccessType] = useState("API");
  const [requiresAuth, setRequiresAuth] = useState(false);
  const [frequency, setFrequency] = useState("Daily");
  const [notes, setNotes] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await api.createComplianceSource({
        source_name: sourceName,
        category,
        official_url: url,
        access_type: accessType,
        requires_auth: requiresAuth,
        update_frequency: frequency,
        notes: notes || null
      });
      setSourceName("");
      setUrl("");
      setNotes("");
      setShowCreateModal(false);
      onRefresh();
    } catch (err: any) {
      setError(err.message || "Failed to register compliance source");
    } finally {
      setLoading(false);
    }
  };

  const isAdmin = currentUser && ["SUPER_ADMIN", "FIRM_ADMIN", "PARTNER"].includes(currentUser.role);

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Compliance Knowledge Registry</h1>
          <p className="text-sm text-slate-500 mt-1">Official regulatory portals, circular specifications, and notifications indexed by CA Intelligence.</p>
        </div>
        {isAdmin && (
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center space-x-2 py-2 px-4 bg-slate-900 text-white rounded-md text-sm font-semibold hover:bg-slate-800 transition-colors"
          >
            <Plus className="h-4 w-4" />
            <span>Add Source</span>
          </button>
        )}
      </div>

      {/* Grid of Sources */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {sources.map((src) => (
          <div key={src.id} className="bg-white border border-slate-200 rounded-lg p-5 card-shadow flex flex-col justify-between">
            <div>
              <div className="flex justify-between items-start mb-3">
                <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                  {src.category}
                </span>
                <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold ${
                  src.status === "ACTIVE" ? "bg-emerald-50 text-emerald-700" : "bg-slate-50 text-slate-600"
                }`}>
                  {src.status}
                </span>
              </div>
              
              <h3 className="font-bold text-slate-900 text-base mb-1">{src.source_name}</h3>
              <p className="text-xs text-slate-500 font-mono truncate mb-4" title={src.official_url}>
                {src.official_url}
              </p>
              
              {src.notes && (
                <p className="text-xs text-slate-600 bg-slate-50 p-2.5 rounded border border-slate-100 mb-4 leading-relaxed">
                  {src.notes}
                </p>
              )}
            </div>

            <div className="border-t border-slate-100 pt-3 flex justify-between items-center text-xs text-slate-500">
              <span className="flex items-center space-x-1">
                <Globe className="h-3.5 w-3.5" />
                <span>{src.access_type}</span>
              </span>
              <span className="flex items-center space-x-1">
                <RefreshCw className="h-3.5 w-3.5 text-slate-400" />
                <span>{src.update_frequency}</span>
              </span>
              <span className="flex items-center">
                {src.requires_auth ? (
                  <span title="Requires Authenticated Connection" className="flex items-center"><ShieldAlert className="h-3.5 w-3.5 text-amber-500 mr-1" /></span>
                ) : (
                  <span title="Public Source" className="flex items-center"><ShieldCheck className="h-3.5 w-3.5 text-emerald-500 mr-1" /></span>
                )}
                <span>{src.requires_auth ? "Auth Required" : "Public"}</span>
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Create Source Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white border border-slate-200 rounded-lg max-w-lg w-full p-6 card-shadow space-y-4">
            <div className="flex justify-between items-center border-b border-slate-100 pb-3">
              <h3 className="text-lg font-bold text-slate-900">Add Custom Compliance Feed</h3>
              <button 
                onClick={() => setShowCreateModal(false)}
                className="text-slate-400 hover:text-slate-600 text-xl font-bold"
              >
                ×
              </button>
            </div>

            {error && (
              <div className="bg-red-50 p-3 rounded text-sm text-red-700">
                {error}
              </div>
            )}

            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700">Source Name *</label>
                <input
                  type="text"
                  required
                  value={sourceName}
                  onChange={(e) => setSourceName(e.target.value)}
                  className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-900 text-sm"
                  placeholder="CBIC GST Rate Finder"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700">Category *</label>
                  <select
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                    className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-900 text-sm"
                  >
                    <option value="Income Tax">Income Tax</option>
                    <option value="GST">GST</option>
                    <option value="Indirect Tax">Indirect Tax</option>
                    <option value="MCA / ROC">MCA / ROC</option>
                    <option value="RBI">RBI</option>
                    <option value="e-Gazette">e-Gazette</option>
                    <option value="Custom Knowledge">Custom Knowledge</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700">Access Method *</label>
                  <select
                    value={accessType}
                    onChange={(e) => setAccessType(e.target.value)}
                    className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-900 text-sm"
                  >
                    <option value="API">API</option>
                    <option value="RSS">RSS Feed</option>
                    <option value="Scraping">Web Scraping</option>
                    <option value="Manual Upload">Manual PDF Feed</option>
                    <option value="Paid API">Official Paid API</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700">Official URL *</label>
                <input
                  type="url"
                  required
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-900 text-sm"
                  placeholder="https://example.gov.in"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700">Update Check Frequency *</label>
                  <select
                    value={frequency}
                    onChange={(e) => setFrequency(e.target.value)}
                    className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-900 text-sm"
                  >
                    <option value="Real-time">Real-time</option>
                    <option value="Daily">Daily</option>
                    <option value="Weekly">Weekly</option>
                    <option value="Monthly">Monthly</option>
                  </select>
                </div>

                <div className="flex items-center h-full pt-4">
                  <input
                    type="checkbox"
                    id="reqAuth"
                    checked={requiresAuth}
                    onChange={(e) => setRequiresAuth(e.target.checked)}
                    className="h-4 w-4 text-blue-900 border-slate-300 rounded focus:ring-blue-900"
                  />
                  <label htmlFor="reqAuth" className="ml-2 text-xs font-semibold text-slate-700 select-none">
                    Requires Authentication
                  </label>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700">Source Notes / Description</label>
                <textarea
                  rows={2}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-900 text-sm"
                  placeholder="Briefly describe what this feed indexes..."
                />
              </div>

              <div className="flex justify-end space-x-3 pt-4 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="py-2 px-4 border border-slate-200 rounded-md text-sm font-semibold text-slate-600 hover:bg-slate-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="py-2 px-4 bg-slate-900 hover:bg-slate-800 text-white rounded-md text-sm font-semibold disabled:opacity-50 transition-colors"
                >
                  {loading ? "Adding..." : "Add Source"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
