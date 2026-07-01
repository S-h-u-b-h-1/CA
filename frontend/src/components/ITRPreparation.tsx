import React, { useState, useEffect } from "react";
import { api } from "../lib/api";
import { 
  CheckCircle, AlertTriangle, AlertCircle, RefreshCw, FileText, 
  IndianRupee, Landmark, TrendingUp, Cpu, Award
} from "lucide-react";

interface ITRPreparationProps {
  clientId: string;
}

export const ITRPreparation: React.FC<ITRPreparationProps> = ({ clientId }) => {
  const [ay, setAy] = useState("2025-26");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // ITR specific data states
  const [profile, setProfile] = useState<any | null>(null);
  const [readiness, setReadiness] = useState<any | null>(null);
  const [actions, setActions] = useState<any[]>([]);
  const [verifications, setVerifications] = useState<any[]>([]);
  
  // Tax Summary for income display
  const [summary, setSummary] = useState<any | null>(null);

  useEffect(() => {
    loadITRData();
  }, [clientId, ay]);

  const loadITRData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [profRes, readRes, actRes, verRes, sumRes] = await Promise.all([
        api.getClientITRProfile(clientId, ay),
        api.getClientITRReadiness(clientId, ay),
        api.getClientITRActions(clientId, ay),
        api.getClientITRVerification(clientId, ay),
        api.getClientTaxSummary(clientId, ay).catch(() => null)
      ]);
      
      setProfile(profRes);
      setReadiness(readRes);
      setActions(actRes || []);
      setVerifications(verRes || []);
      setSummary(sumRes);
    } catch (err: any) {
      console.error(err);
      setError(err.message || "Failed to load ITR preparation intelligence checklist");
    } finally {
      setLoading(false);
    }
  };

  if (loading && !profile) {
    return (
      <div className="flex flex-col items-center justify-center py-20 space-y-3">
        <RefreshCw className="h-8 w-8 text-blue-900 animate-spin" />
        <span className="text-sm text-slate-500 font-semibold">Running ITR preparation engine calculations...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Selector Header */}
      <div className="flex justify-between items-center bg-slate-50 p-4 rounded-lg border border-slate-100">
        <div>
          <h4 className="text-sm font-bold text-slate-700">ITR Preparation Intelligence</h4>
          <p className="text-xs text-slate-400">Reviews uploaded sources and flags outstanding action items before filing returns.</p>
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

      {/* 1. Readiness & Completeness Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Readiness Circular gauge */}
        <div className="bg-white border border-slate-200 p-5 rounded-lg shadow-sm flex flex-col items-center justify-center text-center space-y-3">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">ITR Readiness Score</span>
          <div className="relative flex items-center justify-center">
            {/* Visual Progress Arc */}
            <div className="h-28 w-28 rounded-full border-8 border-slate-100 flex items-center justify-center relative">
              <div 
                className={`absolute inset-0 rounded-full border-8 border-transparent transition-all ${
                  (readiness?.readiness_score || 0) >= 80 
                    ? "border-t-emerald-500 border-r-emerald-500" 
                    : (readiness?.readiness_score || 0) >= 50
                    ? "border-t-amber-500 border-r-amber-500"
                    : "border-t-red-500"
                }`} 
              />
              <span className="text-2xl font-extrabold text-slate-800">
                {readiness?.readiness_score?.toFixed(0) || 0}%
              </span>
            </div>
          </div>
          <span className={`text-[10px] font-extrabold uppercase px-2 py-0.5 rounded ${
            (readiness?.readiness_score || 0) >= 80 
              ? "bg-emerald-50 text-emerald-700" 
              : "bg-amber-50 text-amber-700"
          }`}>
            {(readiness?.readiness_score || 0) >= 80 ? "Ready to File" : "Requires Documents"}
          </span>
        </div>

        {/* Data Completeness */}
        <div className="bg-white border border-slate-200 p-5 rounded-lg shadow-sm space-y-3">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Data Completeness Score</span>
          <div className="space-y-1">
            <span className="text-3xl font-extrabold text-slate-800 block">
              {profile?.data_completeness_score?.toFixed(0) || 0}%
            </span>
            <div className="w-full bg-slate-100 rounded-full h-2">
              <div 
                className="bg-blue-600 h-2 rounded-full transition-all" 
                style={{ width: `${profile?.data_completeness_score || 0}%` }} 
              />
            </div>
          </div>
          <div className="text-xs space-y-1.5 text-slate-500 pt-2 border-t border-slate-50">
            <div className="flex justify-between">
              <span>Required Documents:</span>
              <span className="font-bold text-slate-700">4 total</span>
            </div>
            <div className="flex justify-between">
              <span>Collected:</span>
              <span className="font-semibold text-slate-700">{readiness?.collected_documents?.length || 0}</span>
            </div>
            <div className="flex justify-between">
              <span>Pending checklist:</span>
              <span className="font-semibold text-red-600">{readiness?.missing_documents?.length || 0} missing</span>
            </div>
          </div>
        </div>

        {/* Client ITR Profile Details */}
        <div className="bg-white border border-slate-200 p-5 rounded-lg shadow-sm space-y-3">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">ITR Preparation Profile</span>
          <div className="space-y-2 text-xs">
            <div className="flex justify-between border-b border-slate-50 pb-1.5">
              <span className="text-slate-400 font-medium">PAN Reference:</span>
              <span className="font-mono font-bold text-slate-800">{profile?.pan || "N/A"}</span>
            </div>
            <div className="flex justify-between border-b border-slate-50 pb-1.5">
              <span className="text-slate-400 font-medium">Assessment Year:</span>
              <span className="font-semibold text-slate-800">{profile?.assessment_year || ay}</span>
            </div>
            <div className="flex justify-between border-b border-slate-50 pb-1.5">
              <span className="text-slate-400 font-medium">Financial Year:</span>
              <span className="font-semibold text-slate-800">{profile?.financial_year || "2024-25"}</span>
            </div>
            <div className="flex justify-between border-b border-slate-50 pb-1.5">
              <span className="text-slate-400 font-medium">Preparation Status:</span>
              <span className="font-semibold text-slate-800 capitalize">{profile?.itr_status?.replace('_', ' ') || "Not Started"}</span>
            </div>
          </div>
        </div>
      </div>

      {/* 2. Documents Checklist: Collected vs Missing */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Collected Documents list */}
        <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm space-y-3">
          <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center space-x-1">
            <CheckCircle className="h-4 w-4 text-emerald-500" />
            <span>Documents Received & Verified</span>
          </h4>
          <div className="divide-y divide-slate-100 text-xs">
            {readiness?.collected_documents && readiness.collected_documents.length > 0 ? (
              readiness.collected_documents.map((d: string) => (
                <div key={d} className="py-2.5 flex justify-between items-center">
                  <span className="text-slate-700 font-semibold">{d}</span>
                  <span className="text-[9px] bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-0.5 rounded font-bold uppercase">Collected</span>
                </div>
              ))
            ) : (
              <div className="py-6 text-center text-slate-400 italic">No verification documents received yet.</div>
            )}
          </div>
        </div>

        {/* Missing Documents list */}
        <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm space-y-3">
          <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center space-x-1">
            <AlertTriangle className="h-4 w-4 text-amber-500" />
            <span>Missing Documents Required</span>
          </h4>
          <div className="divide-y divide-slate-100 text-xs">
            {readiness?.missing_documents && readiness.missing_documents.length > 0 ? (
              readiness.missing_documents.map((d: string) => (
                <div key={d} className="py-2.5 flex justify-between items-center">
                  <span className="text-slate-700 font-semibold">{d}</span>
                  <span className="text-[9px] bg-red-50 text-red-700 border border-red-200 px-2 py-0.5 rounded font-bold uppercase">Pending</span>
                </div>
              ))
            ) : (
              <div className="py-6 text-center text-slate-400 italic">All required tax documents collected!</div>
            )}
          </div>
        </div>
      </div>

      {/* 3. Income Summary aggregates */}
      <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm space-y-3">
        <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center space-x-1">
          <TrendingUp className="h-4 w-4 text-slate-400" />
          <span>Consolidated Income Schedule & Tax Summary</span>
        </h4>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-xs pt-2">
          <div className="p-3 bg-slate-50 rounded border border-slate-100">
            <span className="text-[9px] font-bold text-slate-400 block uppercase">Interest Income</span>
            <span className="text-sm font-extrabold text-slate-800 mt-1 block">
              ₹{summary?.interest_income?.toLocaleString("en-IN") || 0}
            </span>
          </div>
          <div className="p-3 bg-slate-50 rounded border border-slate-100">
            <span className="text-[9px] font-bold text-slate-400 block uppercase">Dividend Income</span>
            <span className="text-sm font-extrabold text-slate-800 mt-1 block">
              ₹{summary?.dividend_income?.toLocaleString("en-IN") || 0}
            </span>
          </div>
          <div className="p-3 bg-slate-50 rounded border border-slate-100">
            <span className="text-[9px] font-bold text-slate-400 block uppercase">Salary Income</span>
            <span className="text-sm font-extrabold text-slate-800 mt-1 block">
              ₹{summary?.salary_income?.toLocaleString("en-IN") || 0}
            </span>
          </div>
          <div className="p-3 bg-slate-50 rounded border border-slate-100">
            <span className="text-[9px] font-bold text-slate-400 block uppercase">Securities (Capital Gains)</span>
            <span className="text-sm font-extrabold text-slate-800 mt-1 block">
              ₹{summary?.securities_transactions?.toLocaleString("en-IN") || 0}
            </span>
          </div>
          <div className="p-3 bg-slate-50 rounded border border-slate-100">
            <span className="text-[9px] font-bold text-slate-400 block uppercase">Total TDS credit</span>
            <span className="text-sm font-extrabold text-emerald-700 mt-1 block">
              ₹{summary?.total_tds?.toLocaleString("en-IN") || 0}
            </span>
          </div>
        </div>
      </div>

      {/* 4. Verification Check matrix */}
      <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm space-y-3">
        <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center space-x-1">
          <Cpu className="h-4 w-4 text-slate-400" />
          <span>Verification Rules Checklist Engine</span>
        </h4>
        <div className="border border-slate-100 rounded overflow-hidden">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-150 font-bold text-slate-500">
              <tr>
                <th className="py-2.5 px-4">Verification Check</th>
                <th className="py-2.5 px-4">Description</th>
                <th className="py-2.5 px-4">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {verifications && verifications.length > 0 ? (
                verifications.map((v) => (
                  <tr key={v.id} className="hover:bg-slate-50/50">
                    <td className="py-3 px-4 font-bold text-slate-700">{v.verification_type?.replace('_', ' ')}</td>
                    <td className="py-3 px-4 text-slate-500">{v.description}</td>
                    <td className="py-3 px-4">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-extrabold uppercase ${
                        v.status === "PASS" 
                          ? "bg-emerald-50 text-emerald-800 border border-emerald-200" 
                          : v.status === "WARNING"
                          ? "bg-amber-50 text-amber-800 border border-amber-200"
                          : "bg-red-50 text-red-800 border border-red-200"
                      }`}>
                        {v.status}
                      </span>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={3} className="py-4 text-center text-slate-400 italic">No verification records initialized.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* 5. Action Items Checklist */}
      <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm space-y-4">
        <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center space-x-1">
          <Award className="h-4 w-4 text-slate-400" />
          <span>Filing Preparation Action Items Checklist</span>
        </h4>
        <div className="space-y-3">
          {actions && actions.length > 0 ? (
            actions.map((act) => (
              <div 
                key={act.id} 
                className={`p-4 rounded-lg border flex items-start justify-between space-x-3 ${
                  act.severity === "CRITICAL"
                    ? "bg-red-50/50 border-red-200/65"
                    : act.severity === "WARNING"
                    ? "bg-amber-50/50 border-amber-200/65"
                    : "bg-blue-50/50 border-blue-200/65"
                }`}
              >
                <div className="flex items-start space-x-3">
                  {act.severity === "CRITICAL" ? (
                    <AlertCircle className="h-5 w-5 text-red-600 shrink-0 mt-0.5" />
                  ) : act.severity === "WARNING" ? (
                    <AlertTriangle className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
                  ) : (
                    <CheckCircle className="h-5 w-5 text-blue-600 shrink-0 mt-0.5" />
                  )}
                  <div className="space-y-1">
                    <span className={`text-[9px] font-extrabold uppercase px-1.5 py-0.5 rounded ${
                      act.severity === "CRITICAL"
                        ? "bg-red-100 text-red-700"
                        : act.severity === "WARNING"
                        ? "bg-amber-100 text-amber-700"
                        : "bg-blue-100 text-blue-700"
                    }`}>
                      {act.severity}
                    </span>
                    <p className="text-xs text-slate-700 font-semibold leading-relaxed pt-1">
                      {act.action_text}
                    </p>
                  </div>
                </div>
                {act.reference_document && (
                  <span className="text-[10px] font-bold text-slate-400 flex items-center gap-1 bg-slate-50 border border-slate-100 px-2 py-0.5 rounded shrink-0">
                    <FileText className="h-3 w-3" />
                    {act.reference_document}
                  </span>
                )}
              </div>
            ))
          ) : (
            <div className="text-center py-6 text-slate-400 text-xs italic">
              No preparation actions found. Return is ready to file!
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
