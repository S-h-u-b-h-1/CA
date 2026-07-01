import React, { useState, useEffect } from "react";
import { api } from "../lib/api";
import { 
  CheckCircle, AlertTriangle, AlertCircle, RefreshCw, FileText, 
  ArrowLeft, Search, Table, HelpCircle
} from "lucide-react";

interface TISViewProps {
  documentId: string;
  onBack?: () => void;
}

export const TISView: React.FC<TISViewProps> = ({ documentId, onBack }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<any | null>(null);
  const [searchTerm, setSearchTerm] = useState("");

  useEffect(() => {
    loadTIS();
  }, [documentId]);

  const loadTIS = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getDocumentTIS(documentId);
      setData(res);
    } catch (err: any) {
      console.error(err);
      setError(err.message || "Failed to load TIS document entries");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 space-y-3">
        <RefreshCw className="h-8 w-8 text-blue-900 animate-spin" />
        <span className="text-sm text-slate-500 font-semibold">Extracting and parsing TIS structures...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-4">
        {onBack && (
          <button onClick={onBack} className="flex items-center space-x-2 text-xs font-bold text-slate-500 hover:text-slate-700">
            <ArrowLeft className="h-4 w-4" />
            <span>Back to Documents</span>
          </button>
        )}
        <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-md text-xs font-semibold">
          Error: {error}
        </div>
      </div>
    );
  }

  const summary = data?.summary || {};
  const entries = data?.entries || [];

  const filteredEntries = entries.filter((e: any) => {
    const text = (e.category || "") + " " + (e.subcategory || "") + " " + (e.raw_row_text || "");
    return text.toLowerCase().includes(searchTerm.toLowerCase());
  });

  return (
    <div className="space-y-6">
      {/* Header and Back Button */}
      <div className="flex justify-between items-center pb-4 border-b border-slate-100">
        <div className="flex items-center space-x-3">
          {onBack && (
            <button onClick={onBack} className="p-1.5 hover:bg-slate-100 rounded-full border border-slate-200 mr-1">
              <ArrowLeft className="h-4 w-4 text-slate-500" />
            </button>
          )}
          <div>
            <span className="text-[10px] bg-indigo-50 text-indigo-700 border border-indigo-200 px-2 py-0.5 rounded font-bold uppercase">
              Taxpayer Information Summary (TIS)
            </span>
            <h3 className="text-lg font-extrabold text-slate-900 mt-1">Structured TIS Document Details</h3>
          </div>
        </div>
        <button onClick={loadTIS} className="p-1.5 hover:bg-slate-100 rounded border border-slate-200">
          <RefreshCw className="h-4 w-4 text-slate-500" />
        </button>
      </div>

      {/* Overview Metadata Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-slate-50 border border-slate-100 p-4 rounded-lg">
          <span className="text-[9px] font-bold text-slate-400 block uppercase">PAN Reference</span>
          <span className="text-sm font-mono font-bold text-slate-800 mt-1 block">{summary.pan || "N/A"}</span>
        </div>
        <div className="bg-slate-50 border border-slate-100 p-4 rounded-lg">
          <span className="text-[9px] font-bold text-slate-400 block uppercase">Assessment Year</span>
          <span className="text-sm font-bold text-slate-800 mt-1 block">{summary.assessment_year || "N/A"}</span>
        </div>
        <div className="bg-slate-50 border border-slate-100 p-4 rounded-lg">
          <span className="text-[9px] font-bold text-slate-400 block uppercase">Total Reported Value</span>
          <span className="text-sm font-extrabold text-slate-800 mt-1 block">₹{summary.total_reported_value?.toLocaleString("en-IN") || 0}</span>
        </div>
        <div className="bg-slate-50 border border-slate-100 p-4 rounded-lg">
          <span className="text-[9px] font-bold text-slate-400 block uppercase">Total Feedback Value</span>
          <span className="text-sm font-extrabold text-emerald-700 mt-1 block">₹{summary.total_feedback_value?.toLocaleString("en-IN") || 0}</span>
        </div>
      </div>

      {/* Comparison: Derived vs Feedback Values chart view */}
      <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm space-y-4">
        <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center space-x-1">
          <Table className="h-4 w-4 text-slate-400" />
          <span>Category aggregates & Value comparisons</span>
        </h4>
        <div className="divide-y divide-slate-100 text-xs">
          {entries.map((e: any, idx: number) => {
            const hasMismatch = Math.abs(e.feedback_value - e.derived_value) > 10;
            return (
              <div key={idx} className="py-3 flex flex-col md:flex-row md:items-center justify-between space-y-2 md:space-y-0">
                <div>
                  <span className="font-bold text-slate-700 block">{e.category}</span>
                  <span className="text-[10px] text-slate-400 mt-0.5 block">{e.subcategory}</span>
                </div>
                <div className="flex items-center space-x-6 shrink-0">
                  <div className="text-right">
                    <span className="text-[9px] font-bold text-slate-400 block uppercase">Reported</span>
                    <span className="font-bold text-slate-700">₹{e.reported_value?.toLocaleString("en-IN")}</span>
                  </div>
                  <div className="text-right">
                    <span className="text-[9px] font-bold text-slate-400 block uppercase">Derived</span>
                    <span className="font-bold text-slate-700">₹{e.derived_value?.toLocaleString("en-IN")}</span>
                  </div>
                  <div className="text-right">
                    <span className="text-[9px] font-bold text-slate-400 block uppercase">Feedback</span>
                    <span className={`font-bold ${hasMismatch ? "text-amber-600" : "text-emerald-700"}`}>
                      ₹{e.feedback_value?.toLocaleString("en-IN")}
                    </span>
                  </div>
                  {hasMismatch ? (
                    <span className="text-[9px] bg-amber-50 text-amber-700 border border-amber-200 px-2 py-0.5 rounded font-bold uppercase flex items-center gap-1">
                      <AlertTriangle className="h-3 w-3" />
                      Feedback Differs
                    </span>
                  ) : (
                    <span className="text-[9px] bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-0.5 rounded font-bold uppercase flex items-center gap-1">
                      <CheckCircle className="h-3 w-3" />
                      Consistent
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Main Entries table */}
      <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm space-y-4">
        <div className="flex justify-between items-center flex-col md:flex-row space-y-2 md:space-y-0">
          <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider">TIS Raw Transaction Logs</h4>
          <div className="relative w-full md:w-64">
            <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-slate-400" />
            <input 
              type="text" 
              placeholder="Search category, values..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="text-xs w-full pl-8 pr-3 py-1.5 border border-slate-200 rounded bg-white font-medium text-slate-700"
            />
          </div>
        </div>

        <div className="border border-slate-100 rounded overflow-hidden">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-150 font-bold text-slate-500">
              <tr>
                <th className="py-2.5 px-4">Category</th>
                <th className="py-2.5 px-4">Subcategory Info</th>
                <th className="py-2.5 px-4 text-right">Reported</th>
                <th className="py-2.5 px-4 text-right">Derived</th>
                <th className="py-2.5 px-4 text-right">Feedback</th>
                <th className="py-2.5 px-4">Raw Content Log</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredEntries.length > 0 ? (
                filteredEntries.map((e: any, idx: number) => (
                  <tr key={idx} className="hover:bg-slate-50/50">
                    <td className="py-3 px-4 font-semibold text-slate-700">{e.category}</td>
                    <td className="py-3 px-4 text-slate-500">{e.subcategory}</td>
                    <td className="py-3 px-4 text-right font-semibold text-slate-700">₹{e.reported_value?.toLocaleString("en-IN")}</td>
                    <td className="py-3 px-4 text-right font-semibold text-slate-700">₹{e.derived_value?.toLocaleString("en-IN")}</td>
                    <td className="py-3 px-4 text-right font-semibold text-emerald-700">₹{e.feedback_value?.toLocaleString("en-IN")}</td>
                    <td className="py-3 px-4 font-mono text-[10px] text-slate-400 truncate max-w-xs">{e.raw_row_text}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="py-4 text-center text-slate-400 italic">No matching TIS records found.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Raw Extracted Text Panel */}
      <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm space-y-3">
        <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center space-x-1">
          <FileText className="h-4 w-4 text-slate-400" />
          <span>Raw OCR Extracted Content Preview</span>
        </h4>
        <pre className="p-4 bg-slate-50 border border-slate-150 rounded text-[10px] font-mono text-slate-500 overflow-x-auto whitespace-pre-wrap leading-relaxed max-h-48">
          {data?.extracted_text_preview || "No OCR preview available."}
        </pre>
      </div>
    </div>
  );
};
