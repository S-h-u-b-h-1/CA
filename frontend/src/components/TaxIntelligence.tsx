import React, { useState, useEffect } from "react";
import { api } from "../lib/api";
import { 
  ShieldAlert, ShieldCheck, ShieldQuestion, FileText, 
  TrendingUp, IndianRupee, Landmark, Layers, AlertTriangle, AlertCircle, RefreshCw
} from "lucide-react";

interface TaxIntelligenceProps {
  clientId: string;
}

export const TaxIntelligence: React.FC<TaxIntelligenceProps> = ({ clientId }) => {
  const [ay, setAy] = useState("2025-26");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Data payload states
  const [profile, setProfile] = useState<any | null>(null);
  const [summary, setSummary] = useState<any | null>(null);
  const [insights, setInsights] = useState<any[]>([]);
  const [matches, setMatches] = useState<any[]>([]);
  const [documents, setDocuments] = useState<any[]>([]);

  useEffect(() => {
    loadTaxIntelligence();
  }, [clientId, ay]);

  const loadTaxIntelligence = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getClientTaxProfile(clientId, ay);
      if (data) {
        setProfile(data.profile);
        setSummary(data.summary);
        setInsights(data.insights || []);
        setMatches(data.matches || []);
        setDocuments(data.documents || []);
      }
    } catch (err: any) {
      console.error(err);
      setError(err.message || "Failed to load client tax intelligence dashboard");
    } finally {
      setLoading(false);
    }
  };

  if (loading && !profile) {
    return (
      <div className="flex flex-col items-center justify-center py-20 space-y-3">
        <RefreshCw className="h-8 w-8 text-blue-900 animate-spin" />
        <span className="text-sm text-slate-500 font-semibold">Generating Client Tax Intelligence report...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Selection Header */}
      <div className="flex justify-between items-center bg-slate-50 p-4 rounded-lg border border-slate-100">
        <div>
          <h4 className="text-sm font-bold text-slate-700">Select Assessment Year</h4>
          <p className="text-xs text-slate-400">Recomputes matching rules and discrepancy lists automatically.</p>
        </div>
        <div className="flex items-center space-x-2">
          {loading && <RefreshCw className="h-4 w-4 text-blue-900 animate-spin mr-2" />}
          <select 
            value={ay} 
            onChange={(e) => setAy(e.target.value)}
            className="text-xs border border-slate-200 rounded px-3 py-1.5 font-semibold text-slate-700 bg-white"
          >
            <option value="2025-26">AY 2025-26 (FY 2024-25)</option>
            <option value="2024-25">AY 2024-25 (FY 2023-24)</option>
          </select>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-md text-xs font-semibold">
          Error: {error}
        </div>
      )}

      {/* 1. Metric Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white border border-slate-150 p-4 rounded-lg shadow-sm">
          <div className="flex justify-between items-center">
            <span className="text-[10px] font-bold text-slate-400 uppercase">Total Tax Deposited (TDS)</span>
            <IndianRupee className="h-4 w-4 text-emerald-600" />
          </div>
          <span className="block text-lg font-extrabold text-emerald-700 mt-2">
            ₹{summary?.total_tds?.toLocaleString("en-IN") || 0}
          </span>
          <span className="text-[9px] text-slate-400 block mt-1">From {summary?.deductor_count || 0} deductors</span>
        </div>

        <div className="bg-white border border-slate-150 p-4 rounded-lg shadow-sm">
          <div className="flex justify-between items-center">
            <span className="text-[10px] font-bold text-slate-400 uppercase">Total Reported Income</span>
            <TrendingUp className="h-4 w-4 text-blue-600" />
          </div>
          <span className="block text-lg font-extrabold text-blue-900 mt-2">
            ₹{summary?.total_reported_income?.toLocaleString("en-IN") || 0}
          </span>
          <span className="text-[9px] text-slate-400 block mt-1">Across {summary?.ais_category_count || 0} categories</span>
        </div>

        <div className="bg-white border border-slate-150 p-4 rounded-lg shadow-sm">
          <div className="flex justify-between items-center">
            <span className="text-[10px] font-bold text-slate-400 uppercase">Outstanding Demand</span>
            <AlertCircle className="h-4 w-4 text-red-500" />
          </div>
          <span className={`block text-lg font-extrabold mt-2 ${summary?.demand_amount > 0 ? "text-red-600" : "text-slate-700"}`}>
            ₹{summary?.demand_amount?.toLocaleString("en-IN") || 0}
          </span>
          <span className="text-[9px] text-slate-400 block mt-1">Pending rectification check</span>
        </div>

        <div className="bg-white border border-slate-150 p-4 rounded-lg shadow-sm">
          <div className="flex justify-between items-center">
            <span className="text-[10px] font-bold text-slate-400 uppercase">Refund Claimed / Available</span>
            <ShieldCheck className="h-4 w-4 text-teal-600" />
          </div>
          <span className="block text-lg font-extrabold text-teal-700 mt-2">
            ₹{summary?.refund_amount?.toLocaleString("en-IN") || 0}
          </span>
          <span className="text-[9px] text-slate-400 block mt-1">Subject to verification</span>
        </div>
      </div>

      {/* 2. Sub-Category Incomes & SFT Transactions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Income Sources breakdown */}
        <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm space-y-4">
          <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center space-x-1">
            <Landmark className="h-4 w-4 text-slate-400" />
            <span>Aggregate Reported Income Breakdown</span>
          </h4>
          <div className="divide-y divide-slate-100 text-xs">
            <div className="flex justify-between py-2.5">
              <span className="text-slate-600 font-medium">Salary Income:</span>
              <span className="font-bold text-slate-800">₹{summary?.salary_income?.toLocaleString("en-IN") || 0}</span>
            </div>
            <div className="flex justify-between py-2.5">
              <span className="text-slate-600 font-medium">Interest Income:</span>
              <span className="font-bold text-slate-800">₹{summary?.interest_income?.toLocaleString("en-IN") || 0}</span>
            </div>
            <div className="flex justify-between py-2.5">
              <span className="text-slate-600 font-medium">Dividend Income:</span>
              <span className="font-bold text-slate-800">₹{summary?.dividend_income?.toLocaleString("en-IN") || 0}</span>
            </div>
            <div className="flex justify-between py-2.5">
              <span className="text-slate-600 font-medium">Securities Transactions (Shares):</span>
              <span className="font-bold text-slate-800">₹{summary?.securities_transactions?.toLocaleString("en-IN") || 0}</span>
            </div>
            <div className="flex justify-between py-2.5">
              <span className="text-slate-600 font-medium">Mutual Fund Transactions:</span>
              <span className="font-bold text-slate-800">₹{summary?.mutual_fund_transactions?.toLocaleString("en-IN") || 0}</span>
            </div>
          </div>
        </div>

        {/* High-Value / SFT Alerts */}
        <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm space-y-4">
          <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center space-x-1">
            <Layers className="h-4 w-4 text-slate-400" />
            <span>High-Value & SFT Flagged Items</span>
          </h4>
          <div className="divide-y divide-slate-100 text-xs">
            <div className="flex justify-between py-2.5">
              <span className="text-slate-600 font-medium">Property Transactions:</span>
              <span className={`font-bold ${summary?.property_transactions > 0 ? "text-amber-700" : "text-slate-800"}`}>
                ₹{summary?.property_transactions?.toLocaleString("en-IN") || 0}
              </span>
            </div>
            <div className="flex justify-between py-2.5">
              <span className="text-slate-600 font-medium">SFT Reported Transactions:</span>
              <span className={`font-bold ${summary?.sft_transactions > 500000 ? "text-amber-700" : "text-slate-800"}`}>
                ₹{summary?.sft_transactions?.toLocaleString("en-IN") || 0}
              </span>
            </div>
            <div className="flex justify-between py-2.5">
              <span className="text-slate-600 font-medium">High-Value Alarms (&gt;₹2L):</span>
              <span className={`font-extrabold px-2 py-0.5 rounded-full text-[10px] ${summary?.high_value_transactions > 0 ? "bg-amber-50 text-amber-800 border border-amber-200" : "bg-slate-100 text-slate-600"}`}>
                {summary?.high_value_transactions || 0} Transactions
              </span>
            </div>
            <div className="flex justify-between py-2.5">
              <span className="text-slate-600 font-medium">Correlated Documents:</span>
              <span className="font-semibold text-slate-800">
                {summary?.documents_processed || 0} Files
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* 3. Discrepancy Matching Table */}
      <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm space-y-3">
        <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider">Cross-Document Matches & Mismatches</h4>
        <div className="border border-slate-100 rounded overflow-hidden">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-150 font-bold text-slate-500">
              <tr>
                <th className="py-2.5 px-4">Verification Type</th>
                <th className="py-2.5 px-4">Description</th>
                <th className="py-2.5 px-4 text-right">Value (INR)</th>
                <th className="py-2.5 px-4">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {matches && matches.length > 0 ? (
                matches.map((m) => (
                  <tr key={m.id} className="hover:bg-slate-50/50">
                    <td className="py-3 px-4 font-bold text-slate-700">{m.match_type}</td>
                    <td className="py-3 px-4 text-slate-500">{m.description}</td>
                    <td className="py-3 px-4 text-right font-medium">
                      {m.amount > 0 ? `₹${m.amount.toLocaleString("en-IN")}` : "—"}
                    </td>
                    <td className="py-3 px-4">
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-extrabold uppercase ${
                        m.status === "MATCHED" 
                          ? "bg-emerald-50 text-emerald-800 border border-emerald-200" 
                          : "bg-amber-50 text-amber-800 border border-amber-200"
                      }`}>
                        {m.status}
                      </span>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={4} className="py-4 text-center text-slate-400 italic">
                    {documents.length > 0 
                      ? "No discrepancies detected between Form 26AS and AIS datasets."
                      : "Upload Form 26AS and AIS documents to start mismatch verification."
                    }
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* 4. Compliance Insights Timeline */}
      <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm space-y-4">
        <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider">AI Insight Timeline & Compliance Alarms</h4>
        <div className="space-y-3">
          {insights && insights.length > 0 ? (
            insights.map((ins) => (
              <div 
                key={ins.id} 
                className={`p-4 rounded-lg border flex items-start space-x-3 ${
                  ins.severity === "CRITICAL"
                    ? "bg-red-50/50 border-red-200/60"
                    : ins.severity === "WARNING"
                    ? "bg-amber-50/50 border-amber-200/60"
                    : "bg-blue-50/50 border-blue-200/60"
                }`}
              >
                {ins.severity === "CRITICAL" ? (
                  <ShieldAlert className="h-5 w-5 text-red-600 shrink-0 mt-0.5" />
                ) : ins.severity === "WARNING" ? (
                  <AlertTriangle className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
                ) : (
                  <ShieldQuestion className="h-5 w-5 text-blue-600 shrink-0 mt-0.5" />
                )}
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <span className={`text-[9px] font-extrabold uppercase px-1.5 py-0.5 rounded ${
                      ins.severity === "CRITICAL"
                        ? "bg-red-100 text-red-700"
                        : ins.severity === "WARNING"
                        ? "bg-amber-100 text-amber-700"
                        : "bg-blue-100 text-blue-700"
                    }`}>
                      {ins.severity}
                    </span>
                    <span className="text-[10px] text-slate-400 font-mono">Confidence: {(ins.confidence * 100).toFixed(0)}%</span>
                  </div>
                  <p className="text-xs text-slate-700 leading-relaxed font-semibold">
                    {ins.description}
                  </p>
                </div>
              </div>
            ))
          ) : (
            <div className="text-center py-8 text-slate-400 text-xs">
              No compliance insight alarms generated for AY {ay}.
            </div>
          )}
        </div>
      </div>

      {/* 5. Document Status History */}
      <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm space-y-3">
        <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider">Source Documents Mapping & Processing History</h4>
        <div className="divide-y divide-slate-100">
          {documents && documents.length > 0 ? (
            documents.map((d) => (
              <div key={d.id} className="py-3 flex justify-between items-center text-xs">
                <div className="flex items-center space-x-2.5">
                  <FileText className="h-4 w-4 text-slate-400" />
                  <div>
                    <span className="font-bold text-slate-800 block">{d.name}</span>
                    <span className="text-[10px] text-slate-400">Uploaded {d.created_at ? new Date(d.created_at).toLocaleDateString() : "N/A"}</span>
                  </div>
                </div>
                <div className="flex items-center space-x-3">
                  <span className="px-2 py-0.5 bg-slate-100 text-slate-600 font-extrabold text-[9px] rounded-full uppercase tracking-wider">
                    {d.category || "General"}
                  </span>
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                    d.processing_status === "COMPLETED" 
                      ? "bg-emerald-50 text-emerald-700" 
                      : "bg-amber-50 text-amber-700"
                  }`}>
                    {d.processing_status}
                  </span>
                </div>
              </div>
            ))
          ) : (
            <div className="text-center py-4 text-slate-400 text-xs">
              No source documents linked to this client yet.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
