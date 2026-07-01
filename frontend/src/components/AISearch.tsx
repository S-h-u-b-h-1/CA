import React, { useState } from "react";
import { api } from "../lib/api";
import { Search, Loader2, Sparkles, Users, FileText, FileCode, ArrowRight } from "lucide-react";

interface AISearchProps {
  onOpenClient: (client: any) => void;
  onOpenDocument: (doc: any) => void;
}

export const AISearch: React.FC<AISearchProps> = ({ onOpenClient, onOpenDocument }) => {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.search(query);
      setResults(data);
    } catch (err: any) {
      setError(err.message || "Search failed");
    } finally {
      setLoading(false);
    }
  };

  const hasResults = results && (
    results.clients.length > 0 || 
    results.documents.length > 0 || 
    results.notes.length > 0
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight flex items-center space-x-2">
          <Sparkles className="h-6 w-6 text-blue-900 shrink-0" />
          <span>Universal AI Search</span>
        </h1>
        <p className="text-sm text-slate-500 mt-1">Search instantly across client data sheets, notes, compliance registrations, and extracted text indexes.</p>
      </div>

      {/* Large Search Box */}
      <div className="bg-white border border-slate-200 rounded-lg p-6 card-shadow">
        <form onSubmit={handleSearch} className="flex space-x-3">
          <div className="relative flex-1 rounded-md shadow-sm">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Search className="h-5 w-5 text-slate-400" />
            </div>
            <input
              type="text"
              required
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="block w-full pl-10 pr-3 py-3 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-900 focus:border-blue-900 text-base"
              placeholder="Search by client name, PAN/GSTIN, document categories, notices demand..."
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="flex items-center space-x-2 py-3 px-6 bg-slate-900 hover:bg-slate-800 text-white rounded-md text-sm font-semibold transition-colors disabled:opacity-50"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            <span>Search</span>
          </button>
        </form>
      </div>

      {/* Search results */}
      {loading && !results && (
        <div className="flex flex-col items-center justify-center p-12 space-y-2">
          <Loader2 className="h-8 w-8 text-blue-900 animate-spin" />
          <span className="text-xs text-slate-500 font-semibold">Querying indexes...</span>
        </div>
      )}

      {error && (
        <div className="bg-red-50 p-4 rounded-md text-sm text-red-700">
          {error}
        </div>
      )}

      {results && (
        <div className="space-y-6">
          {!hasResults ? (
            <div className="bg-white border border-slate-200 rounded-lg p-12 text-center text-slate-500">
              No matching records found for "{query}". Try checking name spelling or search by general categories (e.g. "Notice", "GSTIN", "Ram").
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-6">
              
              {/* 1. Client Results */}
              {results.clients.length > 0 && (
                <div className="space-y-3">
                  <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center space-x-1">
                    <Users className="h-4 w-4 text-blue-900" />
                    <span>Client Workspaces ({results.clients.length})</span>
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {results.clients.map((c: any) => (
                      <div
                        key={c.id}
                        onClick={() => onOpenClient(c)}
                        className="bg-white border border-slate-200 rounded-lg p-4 cursor-pointer card-hover card-shadow flex justify-between items-center"
                      >
                        <div>
                          <p className="font-bold text-slate-800">{c.client_name}</p>
                          <p className="text-xs text-slate-500 font-mono">PAN: {c.PAN || "N/A"} | GSTIN: {c.GSTIN || "N/A"}</p>
                        </div>
                        <ArrowRight className="h-4 w-4 text-slate-300" />
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 2. Document Results */}
              {results.documents.length > 0 && (
                <div className="space-y-3">
                  <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center space-x-1">
                    <FileText className="h-4 w-4 text-slate-700" />
                    <span>Documents ({results.documents.length})</span>
                  </h3>
                  <div className="bg-white border border-slate-200 rounded-lg card-shadow overflow-hidden">
                    <table className="w-full text-left text-sm">
                      <tbody className="divide-y divide-slate-100">
                        {results.documents.map((d: any) => (
                          <tr key={d.id} className="hover:bg-slate-50/50 cursor-pointer" onClick={() => onOpenDocument(d)}>
                            <td className="py-3 px-4 font-semibold text-slate-800 flex items-center space-x-2">
                              <FileCode className="h-4 w-4 text-slate-400 shrink-0" />
                              <span className="truncate max-w-[250px]">{d.name}</span>
                            </td>
                            <td className="py-3 px-4 text-xs text-slate-500">{d.category}</td>
                            <td className="py-3 px-4 text-right">
                              <span className="text-xs text-blue-900 font-semibold hover:underline">View Extract</span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* 3. Note Results */}
              {results.notes.length > 0 && (
                <div className="space-y-3">
                  <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center space-x-1">
                    <FileCode className="h-4 w-4 text-amber-600" />
                    <span>Notes ({results.notes.length})</span>
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {results.notes.map((n: any) => (
                      <div key={n.id} className="bg-white border border-slate-200 rounded-lg p-4 card-shadow">
                        <h4 className="font-bold text-slate-800 text-sm mb-1">{n.title}</h4>
                        <p className="text-xs text-slate-600 leading-relaxed line-clamp-3">{n.content}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

            </div>
          )}
        </div>
      )}
    </div>
  );
};
